"""
DMR Login Integration Tests

Tests for authentication and authorization workflows in the DMR system.
Covers session-based authentication, API access control, and user management.
"""

import json
import time
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from patients.models import Patient
from student_groups.models import Note, BloodPressure


class LoginIntegrationTestCase(APITestCase):
    """Base test case for login integration tests"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create test users
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@dmr-test.com',
            password='admin_password_123',
            is_staff=True,
            is_superuser=True
        )
        
        self.doctor_user = User.objects.create_user(
            username='doctor_test',
            email='doctor@dmr-test.com',
            password='doctor_password_123',
            first_name='Dr. John',
            last_name='Smith'
        )
        
        self.nurse_user = User.objects.create_user(
            username='nurse_test',
            email='nurse@dmr-test.com',
            password='nurse_password_123',
            first_name='Jane',
            last_name='Doe'
        )
        
        # Create test patient
        self.test_patient = Patient.objects.create(
            first_name='John',
            last_name='Patient',
            date_of_birth='1990-01-01',
            email='patient@test.com',
            phone_number='+1234567890'
        )
        
        # Login endpoints
        self.login_url = '/api-auth/login/'
        self.logout_url = '/api-auth/logout/'
        
        # API endpoints to test
        self.patients_url = '/api/patients/'
        self.notes_url = '/api/student-groups/notes/'
        self.bp_url = '/api/student-groups/observations/blood-pressures/'


class SessionAuthenticationTests(LoginIntegrationTestCase):
    """Test session-based authentication workflow"""
    
    def test_login_success_with_valid_credentials(self):
        """Test successful login with valid username and password"""
        login_data = {
            'username': 'doctor_test',
            'password': 'doctor_password_123'
        }
        
        response = self.client.post(self.login_url, login_data)
        
        # Should redirect after successful login (302) or return 200
        self.assertIn(response.status_code, [200, 302])
        
        # Check that session is created
        self.assertTrue('sessionid' in response.cookies or 
                       'sessionid' in self.client.session.keys())
        
        print(f"✅ Login successful for user: {login_data['username']}")
    
    def test_login_failure_with_invalid_credentials(self):
        """Test login failure with invalid credentials"""
        invalid_credentials = [
            {'username': 'doctor_test', 'password': 'wrong_password'},
            {'username': 'nonexistent_user', 'password': 'any_password'},
            {'username': '', 'password': 'doctor_password_123'},
            {'username': 'doctor_test', 'password': ''},
        ]
        
        for credentials in invalid_credentials:
            response = self.client.post(self.login_url, credentials)
            
            # Should not create session for invalid credentials
            # Response could be 200 with error or redirect to login
            if response.status_code == 200:
                # If returned to login page, check no session created
                self.assertNotIn('sessionid', response.cookies)
            
            print(f"✅ Login correctly failed for: {credentials['username']}")
    
    def test_logout_clears_session(self):
        """Test that logout properly clears the session"""
        # First login
        login_data = {
            'username': 'doctor_test',
            'password': 'doctor_password_123'
        }
        self.client.post(self.login_url, login_data)
        
        # Then logout
        response = self.client.post(self.logout_url)
        
        # Check session is cleared
        self.assertNotIn('sessionid', response.cookies)
        
        # Verify cannot access protected resources
        api_response = self.client.get(self.patients_url)
        self.assertEqual(api_response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        print("✅ Logout successfully cleared session")


class APIAccessControlTests(LoginIntegrationTestCase):
    """Test API access control with authentication"""
    
    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated requests are denied"""
        protected_endpoints = [
            self.patients_url,
            self.notes_url,
            self.bp_url,
            '/api/patients/1/',
            f'/api/patients/{self.test_patient.id}/files/',
        ]
        
        for endpoint in protected_endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(
                response.status_code, 
                status.HTTP_401_UNAUTHORIZED,
                f"Endpoint {endpoint} should require authentication"
            )
            print(f"✅ Unauthenticated access denied for: {endpoint}")
    
    def test_authenticated_access_allowed(self):
        """Test that authenticated requests are allowed"""
        # Login using session authentication
        self.client.force_login(self.doctor_user)
        
        test_endpoints = [
            (self.patients_url, 'GET'),
            (self.notes_url, 'GET'),
            (self.bp_url, 'GET'),
        ]
        
        for endpoint, method in test_endpoints:
            if method == 'GET':
                response = self.client.get(endpoint)
            elif method == 'POST':
                response = self.client.post(endpoint, {})
            
            # Should not be unauthorized
            self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
            print(f"✅ Authenticated access allowed for: {method} {endpoint}")
    
    def test_session_persistence_across_requests(self):
        """Test that session persists across multiple requests"""
        # Login
        login_data = {
            'username': 'doctor_test',
            'password': 'doctor_password_123'
        }
        self.client.post(self.login_url, login_data)
        
        # Make multiple API requests
        for i in range(3):
            response = self.client.get(self.patients_url)
            self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
            print(f"✅ Request {i+1}: Session maintained")
        
        print("✅ Session persistence verified across multiple requests")


class AuthenticationWorkflowTests(LoginIntegrationTestCase):
    """Test complete authentication workflows"""
    
    def test_complete_login_to_api_workflow(self):
        """Test complete workflow from login to API usage"""
        print("\n🔄 Testing complete login-to-API workflow...")
        
        # Step 1: Login
        login_data = {
            'username': 'doctor_test',
            'password': 'doctor_password_123'
        }
        login_response = self.client.post(self.login_url, login_data)
        self.assertIn(login_response.status_code, [200, 302])
        print("✅ Step 1: Login successful")
        
        # Step 2: Access patient list
        patients_response = self.client.get(self.patients_url)
        self.assertEqual(patients_response.status_code, status.HTTP_200_OK)
        print("✅ Step 2: Patient list accessed")
        
        # Step 3: Create a patient note
        note_data = {
            'patient': self.test_patient.id,
            'content': 'Test note from integration test'
        }
        note_response = self.client.post(self.notes_url, note_data)
        self.assertEqual(note_response.status_code, status.HTTP_201_CREATED)
        print("✅ Step 3: Patient note created")
        
        # Step 4: Record blood pressure
        bp_data = {
            'patient': self.test_patient.id,
            'systolic': 120,
            'diastolic': 80
        }
        bp_response = self.client.post(self.bp_url, bp_data)
        self.assertEqual(bp_response.status_code, status.HTTP_201_CREATED)
        print("✅ Step 4: Blood pressure recorded")
        
        # Step 5: Verify data was created with correct user
        note = Note.objects.get(id=note_response.data['id'])
        self.assertEqual(note.user, self.doctor_user)
        
        bp = BloodPressure.objects.get(id=bp_response.data['id'])
        self.assertEqual(bp.user, self.doctor_user)
        print("✅ Step 5: Data correctly associated with logged-in user")
        
        # Step 6: Logout and verify access is denied
        self.client.post(self.logout_url)
        logout_test_response = self.client.get(self.patients_url)
        self.assertEqual(logout_test_response.status_code, status.HTTP_401_UNAUTHORIZED)
        print("✅ Step 6: Access denied after logout")
        
        print("🎉 Complete workflow test passed!")
    
    def test_multiple_user_sessions(self):
        """Test that different users have separate sessions"""
        print("\n🔄 Testing multiple user sessions...")
        
        # Client 1: Doctor login
        client1 = APIClient()
        doctor_login = {
            'username': 'doctor_test',
            'password': 'doctor_password_123'
        }
        client1.post(self.login_url, doctor_login)
        
        # Client 2: Nurse login  
        client2 = APIClient()
        nurse_login = {
            'username': 'nurse_test',
            'password': 'nurse_password_123'
        }
        client2.post(self.login_url, nurse_login)
        
        # Both should be able to access APIs
        response1 = client1.get(self.patients_url)
        response2 = client2.get(self.patients_url)
        
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        
        # Create notes from both users
        note_data = {
            'patient': self.test_patient.id,
            'content': 'Note from user'
        }
        
        doctor_note = client1.post(self.notes_url, note_data)
        nurse_note = client2.post(self.notes_url, note_data)
        
        self.assertEqual(doctor_note.status_code, status.HTTP_201_CREATED)
        self.assertEqual(nurse_note.status_code, status.HTTP_201_CREATED)
        
        # Verify notes are associated with correct users
        doctor_note_obj = Note.objects.get(id=doctor_note.data['id'])
        nurse_note_obj = Note.objects.get(id=nurse_note.data['id'])
        
        self.assertEqual(doctor_note_obj.user, self.doctor_user)
        self.assertEqual(nurse_note_obj.user, self.nurse_user)
        
        print("✅ Multiple user sessions working correctly")


class SecurityTests(LoginIntegrationTestCase):
    """Test security aspects of authentication"""
    
    def test_session_timeout_behavior(self):
        """Test session behavior (basic test, actual timeout would need settings change)"""
        # Login
        self.client.force_login(self.doctor_user)
        
        # Verify initial access
        response = self.client.get(self.patients_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Simulate some time passing and continued access
        time.sleep(1)  # Short delay for test
        response = self.client.get(self.patients_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        print("✅ Session maintains access over time")
    
    def test_csrf_protection(self):
        """Test CSRF protection on login"""
        # Attempt login without CSRF token (if CSRF is enabled)
        login_data = {
            'username': 'doctor_test',
            'password': 'doctor_password_123'
        }
        
        # For API endpoints, CSRF might be disabled
        # This test verifies the current behavior
        response = self.client.post(self.login_url, login_data)
        
        # Should either succeed (CSRF disabled for API) or fail with CSRF error
        self.assertIn(response.status_code, [200, 302, 403])
        
        print(f"✅ CSRF protection status verified (status: {response.status_code})")
    
    def test_login_rate_limiting_simulation(self):
        """Simulate rapid login attempts (basic test)"""
        invalid_data = {
            'username': 'doctor_test',
            'password': 'wrong_password'
        }
        
        # Attempt multiple failed logins
        for i in range(5):
            response = self.client.post(self.login_url, invalid_data)
            # Should consistently reject invalid credentials
            self.assertNotEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Valid login should still work (no rate limiting implemented)
        valid_data = {
            'username': 'doctor_test',
            'password': 'doctor_password_123'
        }
        response = self.client.post(self.login_url, valid_data)
        self.assertIn(response.status_code, [200, 302])
        
        print("✅ Login attempt behavior verified")


class AdminAccessTests(LoginIntegrationTestCase):
    """Test admin-specific authentication and access"""
    
    def test_admin_login_and_access(self):
        """Test admin user login and access to admin interface"""
        print("\n🔄 Testing admin access...")
        
        # Login as admin
        self.client.force_login(self.admin_user)
        
        # Test API access
        response = self.client.get(self.patients_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        print("✅ Admin can access API endpoints")
        
        # Test admin interface access
        admin_response = self.client.get('/admin/')
        self.assertEqual(admin_response.status_code, status.HTTP_200_OK)
        print("✅ Admin can access admin interface")
        
        # Test admin-specific patient management
        admin_patients_response = self.client.get('/admin/patients/patient/')
        self.assertEqual(admin_patients_response.status_code, status.HTTP_200_OK)
        print("✅ Admin can access patient management")
    
    def test_non_admin_cannot_access_admin(self):
        """Test that non-admin users cannot access admin interface"""
        # Login as regular user
        self.client.force_login(self.doctor_user)
        
        # Should be able to access API
        api_response = self.client.get(self.patients_url)
        self.assertEqual(api_response.status_code, status.HTTP_200_OK)
        
        # Should NOT be able to access admin interface
        admin_response = self.client.get('/admin/')
        self.assertIn(admin_response.status_code, [302, 403])  # Redirect to login or forbidden
        
        print("✅ Non-admin users correctly blocked from admin interface")


class DataIsolationTests(LoginIntegrationTestCase):
    """Test that user data is properly isolated"""
    
    def test_user_data_association(self):
        """Test that created data is properly associated with the logged-in user"""
        print("\n🔄 Testing user data association...")
        
        # Login as doctor
        self.client.force_login(self.doctor_user)
        
        # Create note
        note_data = {
            'patient': self.test_patient.id,
            'content': 'Doctor note for data isolation test'
        }
        response = self.client.post(self.notes_url, note_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify note is associated with doctor
        note = Note.objects.get(id=response.data['id'])
        self.assertEqual(note.user, self.doctor_user)
        self.assertNotEqual(note.user, self.nurse_user)
        
        print("✅ Data correctly associated with logged-in user")
    
    def test_data_access_by_different_users(self):
        """Test that different users can access the same patient data"""
        # Both doctor and nurse should be able to see patient data
        # but their created records should be associated with them
        
        # Doctor creates note
        self.client.force_login(self.doctor_user)
        doctor_note_data = {
            'patient': self.test_patient.id,
            'content': 'Doctor observation'
        }
        doctor_note = self.client.post(self.notes_url, doctor_note_data)
        
        # Nurse creates note
        self.client.force_login(self.nurse_user)
        nurse_note_data = {
            'patient': self.test_patient.id,
            'content': 'Nurse observation'
        }
        nurse_note = self.client.post(self.notes_url, nurse_note_data)
        
        # Both should be able to see all notes for the patient
        doctor_view = self.client.get(self.notes_url)
        self.assertEqual(doctor_view.status_code, status.HTTP_200_OK)
        
        self.client.force_login(self.doctor_user)
        nurse_view = self.client.get(self.notes_url)
        self.assertEqual(nurse_view.status_code, status.HTTP_200_OK)
        
        # Verify correct user associations
        doctor_note_obj = Note.objects.get(id=doctor_note.data['id'])
        nurse_note_obj = Note.objects.get(id=nurse_note.data['id'])
        
        self.assertEqual(doctor_note_obj.user, self.doctor_user)
        self.assertEqual(nurse_note_obj.user, self.nurse_user)
        
        print("✅ Data access and isolation working correctly")


# Test runner functions
def run_login_integration_tests():
    """Run all login integration tests"""
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    if not settings.configured:
        import os
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dmr.settings')
        django.setup()
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    test_modules = [
        'tests.test_login_integration.SessionAuthenticationTests',
        'tests.test_login_integration.APIAccessControlTests',
        'tests.test_login_integration.AuthenticationWorkflowTests',
        'tests.test_login_integration.SecurityTests',
        'tests.test_login_integration.AdminAccessTests',
        'tests.test_login_integration.DataIsolationTests',
    ]
    
    failures = test_runner.run_tests(test_modules)
    return failures


if __name__ == '__main__':
    import sys
    failures = run_login_integration_tests()
    sys.exit(bool(failures))
