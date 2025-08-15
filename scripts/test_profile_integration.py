# File: test_profile_integration.py
"""
Test script to verify profile management integration readiness
"""
import requests
import json
from typing import Dict, Any

class ProfileIntegrationTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api/v1"
        self.token = None
        self.headers = {}
    
    def login(self, email: str = "abereenock95@gmail.com", password: str = "SuperAdmin2025!") -> bool:
        """Login and get access token"""
        try:
            response = requests.post(
                f"{self.api_base}/auth/login",
                data={"username": email, "password": password}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                self.headers = {"Authorization": f"Bearer {self.token}"}
                print(f"✅ Login successful")
                return True
            else:
                print(f"❌ Login failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def test_get_profile(self) -> bool:
        """Test getting user profile"""
        try:
            response = requests.get(
                f"{self.api_base}/profile/me",
                headers=self.headers
            )
            
            if response.status_code == 200:
                profile = response.json()
                print(f"✅ Get profile successful")
                
                # Check required fields
                required_fields = [
                    "id", "email", "full_name", "role", "status", 
                    "is_active", "auth_provider", "created_at"
                ]
                
                missing_fields = [field for field in required_fields if field not in profile]
                if missing_fields:
                    print(f"⚠️  Missing required fields: {missing_fields}")
                    return False
                
                print(f"   📧 Email: {profile.get('email')}")
                print(f"   👤 Name: {profile.get('full_name')}")
                print(f"   🛡️  Role: {profile.get('role')}")
                print(f"   🔐 Auth: {profile.get('auth_provider')}")
                print(f"   📞 Phone: {profile.get('phone_number', 'Not set')}")
                return True
            else:
                print(f"❌ Get profile failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Get profile error: {e}")
            return False
    
    def test_update_profile(self) -> bool:
        """Test updating user profile"""
        try:
            update_data = {
                "phone_number": "+254712345678",
                "department": "IT Administration",
                "job_title": "System Administrator",
                "nationality": "Kenyan"
            }
            
            response = requests.put(
                f"{self.api_base}/profile/me",
                json=update_data,
                headers=self.headers
            )
            
            if response.status_code == 200:
                print(f"✅ Profile update successful")
                
                # Verify the update by getting profile again
                get_response = requests.get(
                    f"{self.api_base}/profile/me",
                    headers=self.headers
                )
                
                if get_response.status_code == 200:
                    profile = get_response.json()
                    updated_phone = profile.get('phone_number')
                    if updated_phone == update_data['phone_number']:
                        print(f"   ✅ Phone number updated: {updated_phone}")
                        return True
                    else:
                        print(f"   ❌ Phone number not updated: {updated_phone}")
                        return False
                return True
            else:
                print(f"❌ Profile update failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Profile update error: {e}")
            return False
    
    def test_editable_fields(self) -> bool:
        """Test getting editable fields"""
        try:
            response = requests.get(
                f"{self.api_base}/profile/editable-fields",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Editable fields retrieved")
                
                # Check required structure
                required_keys = ["basic_fields", "enhanced_fields", "readonly_fields", "can_change_password"]
                missing_keys = [key for key in required_keys if key not in data]
                if missing_keys:
                    print(f"⚠️  Missing keys: {missing_keys}")
                    return False
                
                print(f"   📝 Basic fields: {len(data.get('basic_fields', []))}")
                print(f"   🔧 Enhanced fields: {len(data.get('enhanced_fields', []))}")
                print(f"   🔒 Readonly fields: {len(data.get('readonly_fields', []))}")
                print(f"   🔑 Can change password: {data.get('can_change_password')}")
                
                if 'profile_completion' in data:
                    completion = data['profile_completion']
                    print(f"   📊 Profile completion: {completion.get('percentage', 0)}%")
                
                return True
            else:
                print(f"❌ Editable fields failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Editable fields error: {e}")
            return False
    
    def test_profile_stats(self) -> bool:
        """Test getting profile statistics"""
        try:
            response = requests.get(
                f"{self.api_base}/profile/stats",
                headers=self.headers
            )
            
            if response.status_code == 200:
                stats = response.json()
                print(f"✅ Profile stats retrieved")
                
                print(f"   📅 Account age: {stats.get('account_age_days', 0)} days")
                print(f"   🕐 Last login: {stats.get('last_login', 'Never')}")
                
                if 'profile_completion' in stats:
                    completion = stats['profile_completion']
                    print(f"   📊 Profile: {completion.get('percentage', 0)}% complete")
                
                if 'security_status' in stats:
                    security = stats['security_status']
                    print(f"   🔐 Auth method: {security.get('auth_method')}")
                    print(f"   🔑 Has password: {security.get('has_password')}")
                
                return True
            else:
                print(f"❌ Profile stats failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Profile stats error: {e}")
            return False
    
    def test_password_endpoints(self) -> bool:
        """Test password management endpoints (without actually changing password)"""
        try:
            # Test password policy endpoint
            response = requests.get(f"{self.api_base}/password/password-policy")
            
            if response.status_code == 200:
                policy = response.json()
                print(f"✅ Password policy retrieved")
                print(f"   📋 Min length: {policy.get('requirements', {}).get('min_length', 'Unknown')}")
                print(f"   📝 Rules: {len(policy.get('rules', []))} rules")
                return True
            else:
                print(f"❌ Password policy failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Password endpoints error: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all profile integration tests"""
        print("🧪 PROFILE INTEGRATION TESTS")
        print("=" * 50)
        
        tests = [
            ("Login", self.login),
            ("Get Profile", self.test_get_profile),
            ("Update Profile", self.test_update_profile),
            ("Editable Fields", self.test_editable_fields),
            ("Profile Stats", self.test_profile_stats),
            ("Password Endpoints", self.test_password_endpoints)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n🔍 Testing: {test_name}")
            print("-" * 30)
            try:
                if test_func():
                    passed += 1
                    print(f"✅ {test_name} PASSED")
                else:
                    print(f"❌ {test_name} FAILED")
            except Exception as e:
                print(f"💥 {test_name} CRASHED: {e}")
        
        print(f"\n" + "=" * 50)
        print(f"📊 RESULTS: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED - Ready for frontend integration!")
            return True
        else:
            print("⚠️  Some tests failed - check the issues above")
            return False

def main():
    """Run the integration tests"""
    tester = ProfileIntegrationTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ PROFILE MANAGEMENT IS READY FOR INTEGRATION")
        print("\n🔗 Frontend Integration URLs:")
        print("   GET  /api/v1/profile/me")
        print("   PUT  /api/v1/profile/me")
        print("   GET  /api/v1/profile/editable-fields")
        print("   GET  /api/v1/profile/stats")
        print("   POST /api/v1/password/change-password")
        print("   POST /api/v1/password/request-reset")
        print("   GET  /api/v1/password/password-policy")
    else:
        print("\n❌ ISSUES NEED TO BE FIXED BEFORE INTEGRATION")

if __name__ == "__main__":
    main()