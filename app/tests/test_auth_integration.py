"""
Integration tests for authentication with real database operations
"""
import pytest
from fastapi.testclient import TestClient
import os

# Set test environment before importing app
os.environ["TESTING"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["DB_USER"] = "test"
os.environ["DB_PASS"] = "test"
os.environ["DB_NAME"] = "test"
os.environ["DB_HOST"] = "localhost" 
os.environ["DITAT_TOKEN"] = "test-token"
os.environ["SAMSARA_TOKEN"] = "test-token"
os.environ["DUMMY_TOKEN"] = "test-token"
os.environ["WEBHOOK_TOKEN"] = "test-token"
os.environ["SLACK_BOT_TOKEN"] = "test-token"
os.environ["SLACK_SIGNING_SECRET"] = "test-secret"

from main import app
from models.user import User
from logic.auth.service import UserService
from sqlmodel import Session
from db.database import engine

client = TestClient(app)


class TestAuthIntegration:
    """Integration tests that use the real database"""
    
    def setup_method(self):
        """Create a test user before each test"""
        try:
            with Session(engine) as session:
                # Clean up any existing test user
                existing_user = session.query(User).filter(User.username == "integrationtest").first()
                if existing_user:
                    session.delete(existing_user)
                    session.commit()
                
                # Create test user directly using the service
                test_user = User(
                    username="integrationtest",
                    email="integration@test.com",
                    full_name="Integration Test User",
                    password_hash=UserService.hash_password("testpass123"),
                    status="active",
                    email_verified=True,
                    two_factor_enabled=False
                )
                session.add(test_user)
                session.commit()
                session.refresh(test_user)
                self.test_user = test_user
        except Exception as e:
            # If database operations fail, skip the test
            pytest.skip(f"Database setup failed: {e}")
    
    def teardown_method(self):
        """Clean up after each test"""
        try:
            with Session(engine) as session:
                # Clean up test user
                existing_user = session.query(User).filter(User.username == "integrationtest").first()
                if existing_user:
                    session.delete(existing_user)
                    session.commit()
        except Exception:
            # Ignore cleanup errors
            pass
    
    def test_login_success_integration(self):
        """Test successful login with real user from database"""
        response = client.post(
            "/auth/login",
            data={
                "username": "integrationtest",
                "password": "testpass123",
                "grant_type": "password"
            }
        )
        
        # Should succeed with real database
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert "user" in data
        assert data["user"]["username"] == "integrationtest"
        assert data["user"]["email"] == "integration@test.com"
    
    def test_login_wrong_password_integration(self):
        """Test login with wrong password"""
        response = client.post(
            "/auth/login",
            data={
                "username": "integrationtest",
                "password": "wrongpassword",
                "grant_type": "password"
            }
        )
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()
    
    def test_login_nonexistent_user_integration(self):
        """Test login with user that doesn't exist"""
        response = client.post(
            "/auth/login",
            data={
                "username": "nonexistentuser",
                "password": "anypassword",
                "grant_type": "password"
            }
        )
        
        assert response.status_code == 401
    
    def test_token_refresh_integration(self):
        """Test token refresh with real token"""
        # First, login to get tokens
        login_response = client.post(
            "/auth/login",
            data={
                "username": "integrationtest",
                "password": "testpass123",
                "grant_type": "password"
            }
        )
        
        assert login_response.status_code == 200
        login_data = login_response.json()
        refresh_token = login_data["refresh_token"]
        
        # Use refresh token to get new access token
        refresh_response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()
        assert "access_token" in refresh_data
        assert "refresh_token" in refresh_data
        assert refresh_data["token_type"] == "Bearer"
    
    def test_get_current_user_integration(self):
        """Test getting current user info with real token"""
        # First, login to get access token
        login_response = client.post(
            "/auth/login",
            data={
                "username": "integrationtest",
                "password": "testpass123",
                "grant_type": "password"
            }
        )
        
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        
        # Use access token to get user info
        headers = {"Authorization": f"Bearer {access_token}"}
        me_response = client.get("/auth/me", headers=headers)
        
        assert me_response.status_code == 200
        user_data = me_response.json()
        assert user_data["username"] == "integrationtest"
        assert user_data["email"] == "integration@test.com"
        assert user_data["full_name"] == "Integration Test User"
        assert "password" not in user_data
        assert "password_hash" not in user_data
    
    def test_logout_integration(self):
        """Test logout with real token"""
        # First, login to get access token
        login_response = client.post(
            "/auth/login",
            data={
                "username": "integrationtest",
                "password": "testpass123",
                "grant_type": "password"
            }
        )
        
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        
        # Logout with access token
        headers = {"Authorization": f"Bearer {access_token}"}
        logout_response = client.post("/auth/logout", headers=headers)
        
        assert logout_response.status_code == 200
        assert "logged out" in logout_response.json()["message"].lower()
    
    def test_complete_auth_flow_integration(self):
        """Test complete authentication flow"""
        # 1. Login
        login_response = client.post(
            "/auth/login",
            data={
                "username": "integrationtest",
                "password": "testpass123",
                "grant_type": "password"
            }
        )
        assert login_response.status_code == 200
        login_data = login_response.json()
        access_token = login_data["access_token"]
        refresh_token = login_data["refresh_token"]
        
        # 2. Get user info
        headers = {"Authorization": f"Bearer {access_token}"}
        me_response = client.get("/auth/me", headers=headers)
        assert me_response.status_code == 200
        
        # 3. Refresh token
        refresh_response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert refresh_response.status_code == 200
        new_access_token = refresh_response.json()["access_token"]
        
        # 4. Use new token
        new_headers = {"Authorization": f"Bearer {new_access_token}"}
        me_response2 = client.get("/auth/me", headers=new_headers)
        assert me_response2.status_code == 200
        
        # 5. Logout
        logout_response = client.post("/auth/logout", headers=new_headers)
        assert logout_response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])