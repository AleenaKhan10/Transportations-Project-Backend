"""
Tests for TrailerUnitMapping MotiveId feature.

Test Coverage:
- Upsert with MotiveId (new record)
- Upsert with MotiveId (update existing record)
- Upsert without MotiveId (backward compatibility)
- Get by MotiveId (found)
- Get by MotiveId (not found - 404)
- 409 Conflict for duplicate MotiveId
- GET /motive/{motive_id} requires authentication (401)
- GET /motive/{motive_id} with authentication (200)
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlmodel import Session
from models.trailer_unit_mapping import TrailerUnitMapping
from db.database import engine
from main import app
from logic.auth.security import create_access_token

client = TestClient(app)


class TestTrailerUnitMappingMotiveId:
    """Test MotiveId functionality in TrailerUnitMapping"""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Clean up test data before and after each test"""
        # Setup: Clean any existing test data
        test_units = ["TEST_UNIT_1", "TEST_UNIT_2", "TEST_UNIT_3", "TEST_UNIT_CONFLICT"]
        with Session(engine) as session:
            for unit in test_units:
                existing = session.query(TrailerUnitMapping).filter(
                    TrailerUnitMapping.TrailerUnit == unit
                ).first()
                if existing:
                    session.delete(existing)
            session.commit()

        yield

        # Teardown: Clean up after test
        with Session(engine) as session:
            for unit in test_units:
                existing = session.query(TrailerUnitMapping).filter(
                    TrailerUnitMapping.TrailerUnit == unit
                ).first()
                if existing:
                    session.delete(existing)
            session.commit()

    @pytest.fixture
    def auth_token(self):
        """Generate a valid JWT token for authenticated requests"""
        # Create a test token (assumes user 'testuser' exists or JWT doesn't validate user)
        token, _ = create_access_token(data={"sub": "testuser"})
        return token

    def test_upsert_with_motive_id_new_record(self, auth_token):
        """Test upserting a new record with MotiveId"""
        payload = {
            "TrailerUnit": "TEST_UNIT_1",
            "TrailerID": 12345,
            "MotiveId": 99001
        }

        response = client.post(
            "/trailer-unit-mappings/upsert",
            json=payload,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["TrailerUnit"] == "TEST_UNIT_1"
        assert data["TrailerID"] == 12345
        assert data["MotiveId"] == 99001

    def test_upsert_with_motive_id_update_existing(self, auth_token):
        """Test upserting an existing record to update MotiveId"""
        # Create initial record without MotiveId
        initial_payload = {
            "TrailerUnit": "TEST_UNIT_2",
            "TrailerID": 12346
        }
        client.post(
            "/trailer-unit-mappings/upsert",
            json=initial_payload,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        # Update with MotiveId
        update_payload = {
            "TrailerUnit": "TEST_UNIT_2",
            "MotiveId": 99002
        }
        response = client.post(
            "/trailer-unit-mappings/upsert",
            json=update_payload,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["TrailerUnit"] == "TEST_UNIT_2"
        assert data["TrailerID"] == 12346  # Should be preserved
        assert data["MotiveId"] == 99002

    def test_upsert_without_motive_id_backward_compatibility(self, auth_token):
        """Test that upsert still works without MotiveId (backward compatibility)"""
        payload = {
            "TrailerUnit": "TEST_UNIT_3",
            "TrailerID": 12347
        }

        response = client.post(
            "/trailer-unit-mappings/upsert",
            json=payload,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["TrailerUnit"] == "TEST_UNIT_3"
        assert data["TrailerID"] == 12347
        assert data.get("MotiveId") is None

    def test_get_by_motive_id_found(self, auth_token):
        """Test GET /motive/{motive_id} returns mapping when found"""
        # Create record with MotiveId
        payload = {
            "TrailerUnit": "TEST_UNIT_1",
            "TrailerID": 12345,
            "MotiveId": 99003
        }
        client.post(
            "/trailer-unit-mappings/upsert",
            json=payload,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        # Retrieve by MotiveId
        response = client.get(
            "/trailer-unit-mappings/motive/99003",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["TrailerUnit"] == "TEST_UNIT_1"
        assert data["MotiveId"] == 99003

    def test_get_by_motive_id_not_found(self, auth_token):
        """Test GET /motive/{motive_id} returns 404 when not found"""
        response = client.get(
            "/trailer-unit-mappings/motive/99999",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_conflict_duplicate_motive_id(self, auth_token):
        """Test 409 Conflict when trying to assign duplicate MotiveId to different TrailerUnit"""
        # Create first record with MotiveId
        payload1 = {
            "TrailerUnit": "TEST_UNIT_1",
            "MotiveId": 99004
        }
        client.post(
            "/trailer-unit-mappings/upsert",
            json=payload1,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        # Try to create second record with same MotiveId
        payload2 = {
            "TrailerUnit": "TEST_UNIT_CONFLICT",
            "MotiveId": 99004
        }
        response = client.post(
            "/trailer-unit-mappings/upsert",
            json=payload2,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 409
        assert "already assigned" in response.json()["detail"].lower()

    def test_get_by_motive_id_requires_authentication(self):
        """Test GET /motive/{motive_id} returns 401 without authentication"""
        response = client.get("/trailer-unit-mappings/motive/99005")

        assert response.status_code == 401
        assert "could not validate credentials" in response.json()["detail"].lower()

    def test_model_get_by_motive_id_method(self):
        """Test TrailerUnitMapping.get_by_motive_id() class method"""
        # Create test record directly
        mapping = TrailerUnitMapping(
            TrailerUnit="TEST_UNIT_1",
            TrailerID=12345,
            MotiveId=99006
        )
        with Session(engine) as session:
            session.add(mapping)
            session.commit()

        # Test get_by_motive_id
        result = TrailerUnitMapping.get_by_motive_id(99006)
        assert result is not None
        assert result.TrailerUnit == "TEST_UNIT_1"
        assert result.MotiveId == 99006

        # Test not found
        result_not_found = TrailerUnitMapping.get_by_motive_id(99999)
        assert result_not_found is None

    def test_put_update_motive_id_conflict(self, auth_token):
        """Test PUT returns 409 for duplicate MotiveId on different TrailerUnit"""
        # Create first record with MotiveId
        payload1 = {
            "TrailerUnit": "TEST_UNIT_1",
            "MotiveId": 99007
        }
        client.post(
            "/trailer-unit-mappings/upsert",
            json=payload1,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        # Create second record without MotiveId
        payload2 = {
            "TrailerUnit": "TEST_UNIT_2",
            "TrailerID": 12346
        }
        client.post(
            "/trailer-unit-mappings/upsert",
            json=payload2,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        # Try to update second record with first record's MotiveId
        update_payload = {"MotiveId": 99007}
        response = client.put(
            "/trailer-unit-mappings/TEST_UNIT_2",
            json=update_payload,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 409
        assert "already assigned" in response.json()["detail"].lower()

    def test_post_create_duplicate_motive_id_conflict(self, auth_token):
        """Test POST create returns 409 for duplicate MotiveId"""
        # Create first record with MotiveId
        payload1 = {
            "TrailerUnit": "TEST_UNIT_1",
            "MotiveId": 99008
        }
        client.post(
            "/trailer-unit-mappings/upsert",
            json=payload1,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        # Try to create second record with same MotiveId
        payload2 = {
            "TrailerUnit": "TEST_UNIT_2",
            "MotiveId": 99008
        }
        response = client.post(
            "/trailer-unit-mappings/",
            json=payload2,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 409
        assert "already assigned" in response.json()["detail"].lower()

    def test_upsert_empty_trailer_unit(self, auth_token):
        """Test upsert returns 400 for empty TrailerUnit"""
        payload = {
            "TrailerUnit": "",
            "MotiveId": 99009
        }
        response = client.post(
            "/trailer-unit-mappings/upsert",
            json=payload,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 400
        assert "required" in response.json()["detail"].lower()

    def test_all_endpoints_require_authentication(self):
        """Test that all endpoints require authentication"""
        # GET endpoints
        endpoints_get = [
            "/trailer-unit-mappings/",
            "/trailer-unit-mappings/unit/TEST",
            "/trailer-unit-mappings/trailer/123",
            "/trailer-unit-mappings/motive/456",
        ]
        for endpoint in endpoints_get:
            response = client.get(endpoint)
            assert response.status_code == 401, f"GET {endpoint} should require auth"

        # POST endpoints
        response = client.post(
            "/trailer-unit-mappings/upsert",
            json={"TrailerUnit": "TEST"}
        )
        assert response.status_code == 401, "POST /upsert should require auth"

        response = client.post(
            "/trailer-unit-mappings/",
            json={"TrailerUnit": "TEST"}
        )
        assert response.status_code == 401, "POST / should require auth"

        # PUT endpoint
        response = client.put(
            "/trailer-unit-mappings/TEST",
            json={"TrailerID": 123}
        )
        assert response.status_code == 401, "PUT should require auth"

        # DELETE endpoint
        response = client.delete("/trailer-unit-mappings/TEST")
        assert response.status_code == 401, "DELETE should require auth"

    def test_backward_compatibility_response_includes_motive_id(self, auth_token):
        """Test that response always includes MotiveId field (nullable)"""
        # Create record without MotiveId
        payload = {
            "TrailerUnit": "TEST_UNIT_1",
            "TrailerID": 12345
        }
        client.post(
            "/trailer-unit-mappings/upsert",
            json=payload,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        # Get the record and verify MotiveId field exists
        response = client.get(
            "/trailer-unit-mappings/unit/TEST_UNIT_1",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "MotiveId" in data
        assert data["MotiveId"] is None
