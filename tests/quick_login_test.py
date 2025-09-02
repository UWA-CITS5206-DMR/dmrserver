#!/usr/bin/env python3
"""
Quick Login Test for DMR System

A lightweight script to quickly test login functionality.
Can be run independently without full test setup.
"""

import sys
import os
import json
import requests
import time
from urllib.parse import urljoin

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_dmr_login_quick():
    """Quick login test function"""
    
    base_url = 'http://127.0.0.1:8000'
    
    print("🚀 DMR Quick Login Test")
    print("=" * 30)
    
    # Test 1: Server availability
    print("\n1️⃣ Testing server availability...")
    try:
        response = requests.get(base_url, timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
        else:
            print(f"⚠️ Server responded with status: {response.status_code}")
    except requests.exceptions.RequestException:
        print("❌ Server is not running. Please start it with: ./start.sh dev")
        return False
    
    # Test 2: Login page access
    print("\n2️⃣ Testing login page access...")
    login_url = urljoin(base_url, '/api-auth/login/')
    try:
        response = requests.get(login_url, timeout=5)
        if response.status_code == 200:
            print("✅ Login page accessible")
        else:
            print(f"⚠️ Login page returned: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot access login page: {e}")
        return False
    
    # Test 3: API endpoints without auth (should be denied)
    print("\n3️⃣ Testing unauthenticated API access...")
    test_endpoints = [
        '/api/patients/',
        '/api/student-groups/notes/',
        '/api/student-groups/observations/blood-pressures/'
    ]
    
    for endpoint in test_endpoints:
        try:
            url = urljoin(base_url, endpoint)
            response = requests.get(url, timeout=5)
            if response.status_code == 401:
                print(f"✅ {endpoint}: Correctly denied (401)")
            else:
                print(f"⚠️ {endpoint}: Unexpected response ({response.status_code})")
        except requests.exceptions.RequestException as e:
            print(f"❌ {endpoint}: Error - {e}")
    
    # Test 4: Django admin access
    print("\n4️⃣ Testing Django admin access...")
    try:
        admin_url = urljoin(base_url, '/admin/')
        response = requests.get(admin_url, timeout=5)
        if response.status_code in [200, 302]:
            print("✅ Django admin accessible")
        else:
            print(f"⚠️ Django admin returned: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot access Django admin: {e}")
    
    # Test 5: API schema/documentation
    print("\n5️⃣ Testing API documentation...")
    try:
        schema_url = urljoin(base_url, '/schema/swagger-ui/')
        response = requests.get(schema_url, timeout=5)
        if response.status_code == 200:
            print("✅ API documentation accessible")
        else:
            print(f"⚠️ API docs returned: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot access API docs: {e}")
    
    # Test 6: Basic login attempt (if user exists)
    print("\n6️⃣ Testing basic login functionality...")
    
    # Common default credentials to try
    test_credentials = [
        ('admin', 'admin'),
        ('test', 'test'),
        ('demo', 'demo'),
    ]
    
    session = requests.Session()
    login_successful = False
    
    for username, password in test_credentials:
        try:
            # Get login page to potentially get CSRF token
            login_page = session.get(login_url)
            
            login_data = {
                'username': username,
                'password': password,
            }
            
            # Attempt login
            response = session.post(login_url, data=login_data, allow_redirects=False)
            
            # Check if login was successful
            if response.status_code in [200, 302]:
                # Verify by trying to access protected endpoint
                api_test = session.get(urljoin(base_url, '/api/patients/'))
                if api_test.status_code == 200:
                    print(f"✅ Login successful with {username}/{password}")
                    login_successful = True
                    break
                else:
                    print(f"⚠️ Login attempt with {username}/{password} - unclear result")
            else:
                print(f"❌ Login failed with {username}/{password}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Login attempt error with {username}/{password}: {e}")
    
    if not login_successful:
        print("\n⚠️ No successful login with default credentials.")
        print("💡 To test login functionality:")
        print("   1. Create a user: ./start.sh shell")
        print("   2. Then run: User.objects.create_user('testuser', 'test@test.com', 'testpass')")
        print("   3. Or run the full test suite: ./run_login_tests.sh")
    
    print("\n🏁 Quick test completed!")
    return True


def test_with_custom_credentials():
    """Test with user-provided credentials"""
    
    print("\n🔐 Custom Credential Test")
    print("=" * 25)
    
    username = input("Enter username: ").strip()
    if not username:
        print("❌ Username required")
        return False
    
    password = input("Enter password: ").strip()
    if not password:
        print("❌ Password required")
        return False
    
    base_url = 'http://127.0.0.1:8000'
    login_url = urljoin(base_url, '/api-auth/login/')
    
    session = requests.Session()
    
    try:
        # Get login page
        print("🔍 Accessing login page...")
        login_page = session.get(login_url)
        
        login_data = {
            'username': username,
            'password': password,
        }
        
        print("🔑 Attempting login...")
        response = session.post(login_url, data=login_data, allow_redirects=False)
        
        print(f"📊 Login response status: {response.status_code}")
        
        # Test API access
        print("🧪 Testing API access...")
        api_test = session.get(urljoin(base_url, '/api/patients/'))
        
        if api_test.status_code == 200:
            print("✅ Login successful! Can access protected APIs")
            
            # Test creating a note if possible
            try:
                patients_data = api_test.json()
                if patients_data.get('results'):
                    patient_id = patients_data['results'][0]['id']
                    
                    note_data = {
                        'patient': patient_id,
                        'content': f'Test note from quick test at {time.strftime("%Y-%m-%d %H:%M:%S")}'
                    }
                    
                    note_response = session.post(
                        urljoin(base_url, '/api/student-groups/notes/'),
                        json=note_data
                    )
                    
                    if note_response.status_code == 201:
                        print("✅ Successfully created a test note")
                    else:
                        print(f"⚠️ Could not create test note: {note_response.status_code}")
                
            except Exception as e:
                print(f"⚠️ Error testing note creation: {e}")
                
        elif api_test.status_code == 401:
            print("❌ Login failed - still unauthorized")
        else:
            print(f"⚠️ Unexpected API response: {api_test.status_code}")
        
        # Logout test
        print("🚪 Testing logout...")
        logout_response = session.post(urljoin(base_url, '/api-auth/logout/'))
        print(f"📊 Logout response status: {logout_response.status_code}")
        
        # Verify logout
        logout_test = session.get(urljoin(base_url, '/api/patients/'))
        if logout_test.status_code == 401:
            print("✅ Logout successful - access denied")
        else:
            print("⚠️ Logout may not have worked correctly")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def main():
    """Main function"""
    
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--help', '-h', 'help']:
            print("DMR Quick Login Test")
            print("\nUsage:")
            print("  python quick_login_test.py          # Run quick test")
            print("  python quick_login_test.py custom   # Test with custom credentials")
            print("  python quick_login_test.py --help   # Show this help")
            return
        elif sys.argv[1] == 'custom':
            test_with_custom_credentials()
            return
    
    # Run quick test by default
    test_dmr_login_quick()


if __name__ == '__main__':
    main()
