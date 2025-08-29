import requests
import sys
import json
import time
from datetime import datetime

class MemoryPortalAPITester:
    def __init__(self, base_url="https://remembrance-ai-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.user_id = "test_user_" + datetime.now().strftime('%H%M%S')
        self.profile_id = None
        self.memory_id = None
        self.chat_message_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'} if not files else {}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                if files:
                    response = requests.post(url, data=data, files=files, timeout=30)
                else:
                    response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        return self.run_test("Root API Endpoint", "GET", "", 200)

    def test_create_user_profile(self):
        """Test creating a user profile"""
        profile_data = {
            "id": self.user_id,
            "name": "Test Loved One",
            "personality_traits": "Loving, caring, always supportive, had a great sense of humor and loved spending time with family.",
            "avatar_image_url": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=400&h=400&fit=crop&crop=face"
        }
        
        success, response = self.run_test(
            "Create User Profile",
            "POST",
            "profiles",
            200,
            data=profile_data
        )
        
        if success and 'id' in response:
            self.profile_id = response['id']
            return True
        return False

    def test_get_user_profile(self):
        """Test getting a user profile"""
        if not self.profile_id:
            print("❌ Skipping - No profile ID available")
            return False
            
        return self.run_test(
            "Get User Profile",
            "GET",
            f"profiles/{self.user_id}",
            200
        )[0]

    def test_get_all_profiles(self):
        """Test getting all profiles"""
        return self.run_test(
            "Get All Profiles",
            "GET",
            "profiles",
            200
        )[0]

    def test_create_text_memory(self):
        """Test creating a text memory"""
        memory_data = {
            "user_id": self.user_id,
            "type": "text",
            "content": "I remember when we used to bake cookies together every Christmas morning. The kitchen would smell amazing and you always let me lick the spoon.",
            "description": "Christmas baking memories"
        }
        
        success, response = self.run_test(
            "Create Text Memory",
            "POST",
            "memories",
            200,
            data=memory_data
        )
        
        if success and 'id' in response:
            self.memory_id = response['id']
            return True
        return False

    def test_get_user_memories(self):
        """Test getting user memories"""
        return self.run_test(
            "Get User Memories",
            "GET",
            f"memories/{self.user_id}",
            200
        )[0]

    def test_send_chat_message(self):
        """Test sending a chat message"""
        chat_data = {
            "user_id": self.user_id,
            "message": "Do you remember our Christmas baking traditions?"
        }
        
        print("⏳ Sending chat message (AI response may take time)...")
        success, response = self.run_test(
            "Send Chat Message",
            "POST",
            "chat",
            200,
            data=chat_data
        )
        
        if success:
            print("   AI Response received successfully")
            if 'ai_response' in response:
                print(f"   AI Message: {response['ai_response']['message'][:100]}...")
            return True
        return False

    def test_get_chat_history(self):
        """Test getting chat history"""
        return self.run_test(
            "Get Chat History",
            "GET",
            f"chat/{self.user_id}",
            200
        )[0]

    def test_create_avatar_video(self):
        """Test creating an avatar video"""
        avatar_data = {
            "user_id": self.user_id,
            "image_url": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=400&h=400&fit=crop&crop=face",
            "text": "Hello, I miss you too and I'm always with you in spirit."
        }
        
        print("⏳ Creating avatar video (D-ID API call)...")
        success, response = self.run_test(
            "Create Avatar Video",
            "POST",
            "avatar/create",
            200,
            data=avatar_data
        )
        
        if success and 'talk_id' in response:
            self.talk_id = response['talk_id']
            print(f"   Talk ID: {self.talk_id}")
            return True
        return False

    def test_get_avatar_status(self):
        """Test getting avatar video status"""
        if not hasattr(self, 'talk_id'):
            print("❌ Skipping - No talk ID available")
            return False
            
        return self.run_test(
            "Get Avatar Status",
            "GET",
            f"avatar/{self.talk_id}/status",
            200
        )[0]

    def run_all_tests(self):
        """Run all API tests in sequence"""
        print("🚀 Starting Memory Portal API Tests")
        print(f"   Base URL: {self.base_url}")
        print(f"   Test User ID: {self.user_id}")
        print("=" * 60)

        # Test sequence
        tests = [
            ("Root Endpoint", self.test_root_endpoint),
            ("Create User Profile", self.test_create_user_profile),
            ("Get User Profile", self.test_get_user_profile),
            ("Get All Profiles", self.test_get_all_profiles),
            ("Create Text Memory", self.test_create_text_memory),
            ("Get User Memories", self.test_get_user_memories),
            ("Send Chat Message", self.test_send_chat_message),
            ("Get Chat History", self.test_get_chat_history),
            ("Create Avatar Video", self.test_create_avatar_video),
            ("Get Avatar Status", self.test_get_avatar_status),
        ]

        for test_name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {str(e)}")
            
            # Small delay between tests
            time.sleep(0.5)

        # Print final results
        print("\n" + "=" * 60)
        print(f"📊 Final Results: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return 1

def main():
    tester = MemoryPortalAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())