"""
Simple authentication API tests without database dependencies
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

client = TestClient(app)


class TestAuthEndpoints:
    """Test auth endpoints are accessible"""
    
    def test_auth_endpoints_exist(self):
        """Test that auth endpoints return proper HTTP status codes"""
        
        # Test registration endpoint exists
        response = client.post("/auth/users", json={})
        # Should return 422 (validation error) not 404 (not found)
        assert response.status_code != 404
        
        # Test login endpoint exists  
        response = client.post("/auth/login", data={})
        # Should return 422 (validation error) not 404 (not found)
        assert response.status_code != 404
        
        # Test refresh endpoint exists
        response = client.post("/auth/refresh", json={})
        # Should return 422 or 401, not 404
        assert response.status_code != 404
        
        # Test logout endpoint exists
        response = client.post("/auth/logout")
        # Should return 401 (unauthorized) not 404 (not found)
        assert response.status_code != 404
        
        # Test forgot password endpoint exists
        response = client.post("/auth/forgot-password", json={})
        # Should return 422 (validation error) not 404 (not found)
        assert response.status_code != 404
        
        # Test me endpoint exists
        response = client.get("/auth/me")
        # Should return 401 (unauthorized) not 404 (not found)
        assert response.status_code != 404

    def test_login_validation(self):
        """Test login input validation"""
        # Missing username and password
        response = client.post("/auth/login", data={})
        assert response.status_code == 422
        
        # Missing password
        response = client.post("/auth/login", data={"username": "test"})
        assert response.status_code == 422

    def test_register_requires_auth(self):
        """Test registration requires authentication"""
        # Missing required fields - should return 401 since endpoint requires auth
        response = client.post("/auth/users", json={})
        assert response.status_code == 401
        
        # Valid data but no auth - should return 401
        response = client.post("/auth/users", json={
            "username": "test",
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "testpass123"
        })
        assert response.status_code == 401

    def test_protected_endpoint_unauthorized(self):
        """Test that protected endpoints require authentication"""
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_invalid_token_format(self):
        """Test invalid token format handling"""
        headers = {"Authorization": "InvalidTokenFormat"}
        response = client.get("/auth/me", headers=headers)
        assert response.status_code == 401

    def test_bearer_token_without_token(self):
        """Test Bearer prefix without actual token"""
        headers = {"Authorization": "Bearer"}
        response = client.get("/auth/me", headers=headers)
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])