#!/bin/bash

# DMR Login Integration Tests Runner
# This script runs various login-related tests for the DMR system

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 DMR Login Integration Tests${NC}"
echo -e "${BLUE}==============================${NC}"

# Check if server is running
check_server() {
    echo -e "${YELLOW}🔍 Checking if DMR server is running...${NC}"
    
    if curl -s http://127.0.0.1:8000/ > /dev/null 2>&1; then
        echo -e "${GREEN}✅ DMR server is running${NC}"
        return 0
    else
        echo -e "${RED}❌ DMR server is not running${NC}"
        return 1
    fi
}

# Start server if not running
start_server_if_needed() {
    if ! check_server; then
        echo -e "${YELLOW}🚀 Starting DMR server...${NC}"
        ./start.sh dev-bg
        
        echo -e "${YELLOW}⏳ Waiting for server to start...${NC}"
        sleep 10
        
        if check_server; then
            echo -e "${GREEN}✅ Server started successfully${NC}"
            SERVER_STARTED_BY_SCRIPT=true
        else
            echo -e "${RED}❌ Failed to start server${NC}"
            exit 1
        fi
    fi
}

# Create test users
create_test_users() {
    echo -e "${YELLOW}👥 Creating test users...${NC}"
    
    uv run python manage.py shell << 'EOF'
from django.contrib.auth.models import User
from patients.models import Patient

# Create test users if they don't exist
test_users = [
    {
        'username': 'test_doctor',
        'email': 'doctor@dmr-test.com',
        'password': 'doctor_password_123',
        'first_name': 'Dr. John',
        'last_name': 'Smith'
    },
    {
        'username': 'test_nurse',
        'email': 'nurse@dmr-test.com', 
        'password': 'nurse_password_123',
        'first_name': 'Jane',
        'last_name': 'Doe'
    },
    {
        'username': 'test_admin',
        'email': 'admin@dmr-test.com',
        'password': 'admin_password_123',
        'is_staff': True,
        'is_superuser': True
    }
]

for user_data in test_users:
    username = user_data['username']
    if not User.objects.filter(username=username).exists():
        user = User.objects.create_user(
            username=user_data['username'],
            email=user_data['email'],
            password=user_data['password'],
            first_name=user_data.get('first_name', ''),
            last_name=user_data.get('last_name', '')
        )
        if user_data.get('is_staff'):
            user.is_staff = True
        if user_data.get('is_superuser'):
            user.is_superuser = True
        user.save()
        print(f"✅ Created user: {username}")
    else:
        print(f"ℹ️ User already exists: {username}")

# Create test patient if it doesn't exist
if not Patient.objects.filter(email='test_patient@dmr-test.com').exists():
    patient = Patient.objects.create(
        first_name='John',
        last_name='TestPatient',
        date_of_birth='1990-01-01',
        email='test_patient@dmr-test.com',
        phone_number='+1234567890'
    )
    print(f"✅ Created test patient: {patient.id}")
else:
    print("ℹ️ Test patient already exists")

print("👥 Test users setup completed")
EOF

    echo -e "${GREEN}✅ Test users created${NC}"
}

# Run Django integration tests
run_django_tests() {
    echo -e "${YELLOW}🧪 Running Django integration tests...${NC}"
    
    # Run the specific login integration tests
    uv run python manage.py test tests.test_login_integration --verbosity=2
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Django integration tests passed${NC}"
    else
        echo -e "${RED}❌ Django integration tests failed${NC}"
        return 1
    fi
}

# Run manual testing script
run_manual_tests() {
    echo -e "${YELLOW}🔧 Running manual login tests...${NC}"
    
    # Run the manual testing script with test credentials
    python3 << 'EOF'
import sys
import os
sys.path.append('.')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dmr.settings')

import django
django.setup()

from tests.test_login_manual import DMRLoginTester

def run_automated_manual_tests():
    tester = DMRLoginTester()
    
    if not tester.test_server_availability():
        print("❌ Server not available for manual tests")
        return False
    
    # Test with the created test users
    test_scenarios = [
        ('test_doctor', 'doctor_password_123'),
        ('test_nurse', 'nurse_password_123'),
        ('test_admin', 'admin_password_123'),
    ]
    
    all_passed = True
    for username, password in test_scenarios:
        print(f"\n🧪 Testing scenario: {username}")
        try:
            success = tester.run_complete_test_scenario(username, password)
            if not success:
                all_passed = False
        except Exception as e:
            print(f"❌ Test scenario failed: {e}")
            all_passed = False
    
    return all_passed

if run_automated_manual_tests():
    print("\n✅ All manual test scenarios passed")
else:
    print("\n❌ Some manual test scenarios failed")
    exit(1)
EOF

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Manual tests completed successfully${NC}"
    else
        echo -e "${RED}❌ Manual tests failed${NC}"
        return 1
    fi
}

# API endpoint testing
test_api_endpoints() {
    echo -e "${YELLOW}🌐 Testing API endpoints...${NC}"
    
    # Test unauthenticated access (should be denied)
    echo -e "${BLUE}Testing unauthenticated access...${NC}"
    
    endpoints=(
        "/api/patients/"
        "/api/student-groups/notes/"
        "/api/student-groups/observations/blood-pressures/"
    )
    
    for endpoint in "${endpoints[@]}"; do
        response=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8000${endpoint}")
        if [ "$response" = "401" ]; then
            echo -e "✅ ${endpoint}: Correctly denied (401)"
        else
            echo -e "⚠️ ${endpoint}: Unexpected response (${response})"
        fi
    done
    
    echo -e "${GREEN}✅ API endpoint tests completed${NC}"
}

# Performance testing
test_login_performance() {
    echo -e "${YELLOW}⚡ Testing login performance...${NC}"
    
    python3 << 'EOF'
import time
import requests
import statistics

def test_login_performance():
    login_url = 'http://127.0.0.1:8000/api-auth/login/'
    logout_url = 'http://127.0.0.1:8000/api-auth/logout/'
    
    credentials = {
        'username': 'test_doctor',
        'password': 'doctor_password_123'
    }
    
    times = []
    
    for i in range(5):
        session = requests.Session()
        
        start_time = time.time()
        response = session.post(login_url, data=credentials)
        end_time = time.time()
        
        login_time = end_time - start_time
        times.append(login_time)
        
        # Logout to clean up
        session.post(logout_url)
        
        print(f"Login attempt {i+1}: {login_time:.3f}s")
    
    avg_time = statistics.mean(times)
    print(f"\n📊 Average login time: {avg_time:.3f}s")
    
    if avg_time < 1.0:
        print("✅ Login performance is good")
    elif avg_time < 2.0:
        print("⚠️ Login performance is acceptable") 
    else:
        print("❌ Login performance is slow")

test_login_performance()
EOF

    echo -e "${GREEN}✅ Performance tests completed${NC}"
}

# Cleanup function
cleanup() {
    if [ "$SERVER_STARTED_BY_SCRIPT" = true ]; then
        echo -e "${YELLOW}🧹 Cleaning up - stopping server...${NC}"
        ./start.sh stop
    fi
}

# Main execution
main() {
    local test_type=${1:-"all"}
    
    # Set up cleanup trap
    trap cleanup EXIT
    
    case $test_type in
        "django")
            start_server_if_needed
            create_test_users
            run_django_tests
            ;;
        "manual")
            start_server_if_needed
            create_test_users
            run_manual_tests
            ;;
        "api")
            start_server_if_needed
            test_api_endpoints
            ;;
        "performance")
            start_server_if_needed
            create_test_users
            test_login_performance
            ;;
        "all")
            start_server_if_needed
            create_test_users
            echo -e "\n${BLUE}Running all test suites...${NC}\n"
            
            run_django_tests
            echo -e "\n${BLUE}================================${NC}\n"
            
            run_manual_tests  
            echo -e "\n${BLUE}================================${NC}\n"
            
            test_api_endpoints
            echo -e "\n${BLUE}================================${NC}\n"
            
            test_login_performance
            ;;
        "help"|"--help"|"-h")
            echo -e "${BLUE}Usage: $0 [test_type]${NC}"
            echo ""
            echo -e "${YELLOW}Test Types:${NC}"
            echo -e "  django      - Run Django integration tests"
            echo -e "  manual      - Run manual testing scenarios"
            echo -e "  api         - Test API endpoints"
            echo -e "  performance - Test login performance"
            echo -e "  all         - Run all tests (default)"
            echo -e "  help        - Show this help message"
            echo ""
            echo -e "${YELLOW}Examples:${NC}"
            echo -e "  $0           # Run all tests"
            echo -e "  $0 django    # Run only Django tests"
            echo -e "  $0 manual    # Run only manual tests"
            ;;
        *)
            echo -e "${RED}❌ Unknown test type: $test_type${NC}"
            echo -e "${YELLOW}Use '$0 help' to see available options${NC}"
            exit 1
            ;;
    esac
    
    echo -e "\n${GREEN}🎉 Login testing completed!${NC}"
}

# Run main function with all arguments
main "$@"
