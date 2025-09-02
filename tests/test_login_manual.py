"""
Manual Login Testing Script

This script provides manual testing utilities for the DMR login system.
Can be run independently or integrated into automated test suites.
"""

import requests
import json
import time
from urllib.parse import urljoin


class DMRLoginTester:
    """Manual testing utility for DMR login functionality"""
    
    def __init__(self, base_url='http://127.0.0.1:8000'):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DMR-Test-Client/1.0'
        })
        
        # Endpoints
        self.login_url = urljoin(base_url, '/api-auth/login/')
        self.logout_url = urljoin(base_url, '/api-auth/logout/')
        self.patients_url = urljoin(base_url, '/api/patients/')
        self.notes_url = urljoin(base_url, '/api/student-groups/notes/')
        self.bp_url = urljoin(base_url, '/api/student-groups/observations/blood-pressures/')
        self.admin_url = urljoin(base_url, '/admin/')
    
    def test_server_availability(self):
        """Test if the DMR server is running"""
        try:
            response = self.session.get(self.base_url, timeout=5)
            if response.status_code == 200:
                print("✅ DMR server is running")
                return True
            else:
                print(f"⚠️ DMR server responded with status: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Cannot connect to DMR server: {e}")
            return False
    
    def get_csrf_token(self):
        """Get CSRF token from login page"""
        try:
            response = self.session.get(self.login_url)
            if 'csrftoken' in response.cookies:
                csrf_token = response.cookies['csrftoken']
                print(f"✅ CSRF token obtained: {csrf_token[:10]}...")
                return csrf_token
            else:
                print("⚠️ No CSRF token found")
                return None
        except Exception as e:
            print(f"❌ Error getting CSRF token: {e}")
            return None
    
    def login(self, username, password, use_csrf=True):
        """Attempt to login with given credentials"""
        print(f"\n🔐 Attempting login for user: {username}")
        
        login_data = {
            'username': username,
            'password': password,
        }
        
        # Get CSRF token if needed
        if use_csrf:
            csrf_token = self.get_csrf_token()
            if csrf_token:
                login_data['csrfmiddlewaretoken'] = csrf_token
                self.session.headers.update({'X-CSRFToken': csrf_token})
        
        try:
            response = self.session.post(
                self.login_url, 
                data=login_data,
                allow_redirects=False
            )
            
            print(f"Login response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            
            # Check for session cookie
            if 'sessionid' in response.cookies:
                print("✅ Session cookie received")
                return True
            elif response.status_code in [200, 302]:
                print("✅ Login appears successful (checking API access...)")
                return self.verify_authenticated_access()
            else:
                print(f"❌ Login failed with status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def verify_authenticated_access(self):
        """Verify that we can access authenticated endpoints"""
        try:
            response = self.session.get(self.patients_url)
            if response.status_code == 200:
                print("✅ Can access patients API - authentication confirmed")
                return True
            elif response.status_code == 401:
                print("❌ Cannot access patients API - authentication failed")
                return False
            else:
                print(f"⚠️ Unexpected response from patients API: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error checking authenticated access: {e}")
            return False
    
    def test_api_endpoints(self):
        """Test various API endpoints after login"""
        print("\n📡 Testing API endpoints...")
        
        endpoints = [
            ('GET', self.patients_url, 'Patients list'),
            ('GET', self.notes_url, 'Notes list'),
            ('GET', self.bp_url, 'Blood pressure list'),
        ]
        
        results = {}
        
        for method, url, description in endpoints:
            try:
                if method == 'GET':
                    response = self.session.get(url)
                elif method == 'POST':
                    response = self.session.post(url, json={})
                
                results[description] = {
                    'status': response.status_code,
                    'success': response.status_code in [200, 201]
                }
                
                if response.status_code == 200:
                    print(f"✅ {description}: {response.status_code}")
                elif response.status_code == 401:
                    print(f"❌ {description}: Unauthorized (401)")
                else:
                    print(f"⚠️ {description}: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ {description}: Error - {e}")
                results[description] = {'status': 'Error', 'success': False}
        
        return results
    
    def create_test_data(self, patient_id=None):
        """Create test data after login"""
        print("\n📝 Creating test data...")
        
        # If no patient_id provided, try to get first patient or create one
        if not patient_id:
            patients_response = self.session.get(self.patients_url)
            if patients_response.status_code == 200:
                patients_data = patients_response.json()
                if patients_data.get('results'):
                    patient_id = patients_data['results'][0]['id']
                    print(f"Using existing patient ID: {patient_id}")
                else:
                    # Create a test patient
                    patient_data = {
                        'first_name': 'Test',
                        'last_name': 'Patient',
                        'date_of_birth': '1990-01-01',
                        'email': f'test_patient_{int(time.time())}@test.com'
                    }
                    
                    create_response = self.session.post(self.patients_url, json=patient_data)
                    if create_response.status_code == 201:
                        patient_id = create_response.json()['id']
                        print(f"✅ Created test patient with ID: {patient_id}")
                    else:
                        print(f"❌ Failed to create test patient: {create_response.status_code}")
                        return False
        
        # Create a test note
        note_data = {
            'patient': patient_id,
            'content': f'Test note created at {time.strftime("%Y-%m-%d %H:%M:%S")}'
        }
        
        note_response = self.session.post(self.notes_url, json=note_data)
        if note_response.status_code == 201:
            print(f"✅ Created test note: {note_response.json()['id']}")
        else:
            print(f"❌ Failed to create test note: {note_response.status_code}")
            print(f"Response: {note_response.text}")
        
        # Create test blood pressure reading
        bp_data = {
            'patient': patient_id,
            'systolic': 120,
            'diastolic': 80
        }
        
        bp_response = self.session.post(self.bp_url, json=bp_data)
        if bp_response.status_code == 201:
            print(f"✅ Created test blood pressure reading: {bp_response.json()['id']}")
        else:
            print(f"❌ Failed to create blood pressure reading: {bp_response.status_code}")
            print(f"Response: {bp_response.text}")
        
        return True
    
    def logout(self):
        """Logout from the system"""
        print("\n🚪 Logging out...")
        
        try:
            response = self.session.post(self.logout_url)
            print(f"Logout response status: {response.status_code}")
            
            # Verify logout by trying to access protected endpoint
            test_response = self.session.get(self.patients_url)
            if test_response.status_code == 401:
                print("✅ Logout successful - access to protected resources denied")
                return True
            else:
                print(f"⚠️ Logout may have failed - still can access protected resources")
                return False
                
        except Exception as e:
            print(f"❌ Logout error: {e}")
            return False
    
    def run_complete_test_scenario(self, username, password):
        """Run a complete test scenario"""
        print(f"\n🧪 Running complete test scenario for user: {username}")
        print("=" * 60)
        
        # Step 1: Check server availability
        if not self.test_server_availability():
            return False
        
        # Step 2: Login
        if not self.login(username, password):
            return False
        
        # Step 3: Test API endpoints
        api_results = self.test_api_endpoints()
        
        # Step 4: Create test data
        self.create_test_data()
        
        # Step 5: Logout
        self.logout()
        
        print("\n✅ Complete test scenario finished")
        return True


def run_manual_login_tests():
    """Run manual login tests with predefined test cases"""
    print("🚀 DMR Login Manual Testing")
    print("=" * 50)
    
    tester = DMRLoginTester()
    
    # Test server availability first
    if not tester.test_server_availability():
        print("❌ Server is not available. Please start the DMR server first:")
        print("   ./start.sh dev")
        return False
    
    # Test cases - you may need to create these users first
    test_users = [
        {'username': 'admin', 'password': 'admin'},  # Default Django admin
        {'username': 'testuser', 'password': 'testpass123'},
        {'username': 'doctor', 'password': 'doctor123'},
    ]
    
    print("\n⚠️ Note: Make sure you have created test users in the system")
    print("You can create users using: ./start.sh shell")
    print("Then: User.objects.create_user('username', 'email@test.com', 'password')")
    
    # Interactive test selection
    print("\nAvailable tests:")
    print("1. Test with predefined users")
    print("2. Test with custom credentials")
    print("3. Test server endpoints only")
    
    choice = input("\nSelect test option (1-3): ").strip()
    
    if choice == '1':
        for user in test_users:
            try:
                tester.run_complete_test_scenario(user['username'], user['password'])
                print("\n" + "-" * 50)
            except KeyboardInterrupt:
                print("\n🛑 Test interrupted by user")
                break
    
    elif choice == '2':
        username = input("Enter username: ").strip()
        password = input("Enter password: ").strip()
        tester.run_complete_test_scenario(username, password)
    
    elif choice == '3':
        tester.test_api_endpoints()
    
    else:
        print("Invalid choice. Running basic server test...")
        tester.test_server_availability()
    
    print("\n🏁 Manual testing completed")
    return True


if __name__ == '__main__':
    run_manual_login_tests()
