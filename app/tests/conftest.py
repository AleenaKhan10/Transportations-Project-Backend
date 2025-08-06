"""
Pytest configuration and shared fixtures for all tests
"""
import pytest
import os
from typing import Generator
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool

# Set test environment
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
from models.user import User, Role, Permission, UserRole, RolePermission
from logic.auth.service import UserService


@pytest.fixture(name="engine")
def engine_fixture():
    """Create a test database engine"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(name="session")
def session_fixture(engine) -> Generator[Session, None, None]:
    """Create a test database session"""
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture() -> Generator[TestClient, None, None]:
    """Create a test client"""
    with TestClient(app) as client:
        yield client


@pytest.fixture(name="test_user")
def test_user_fixture(session: Session) -> User:
    """Create a test user"""
    user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        phone="+1234567890",
        password_hash=UserService.hash_password("testpass123"),
        status="active",
        email_verified=True,
        two_factor_enabled=False,
        department="Testing"
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="admin_user")
def admin_user_fixture(session: Session, admin_role) -> User:
    """Create an admin user with admin role"""
    user = User(
        username="adminuser",
        email="admin@example.com",
        full_name="Admin User",
        password_hash=UserService.hash_password("adminpass123"),
        status="active",
        email_verified=True,
        two_factor_enabled=False
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Assign admin role
    user_role = UserRole(
        user_id=user.id,
        role_id=admin_role.id,
        assigned_by=user.id
    )
    session.add(user_role)
    session.commit()
    
    return user


@pytest.fixture(name="inactive_user")
def inactive_user_fixture(session: Session) -> User:
    """Create an inactive test user"""
    user = User(
        username="inactive",
        email="inactive@example.com",
        full_name="Inactive User",
        password_hash=UserService.hash_password("inactivepass123"),
        status="inactive",
        email_verified=False,
        two_factor_enabled=False
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="admin_role")
def admin_role_fixture(session: Session) -> Role:
    """Create an admin role with full permissions"""
    # Create all permissions
    permissions = [
        Permission(name="read_users", resource="users", action="read", description="Read user data"),
        Permission(name="write_users", resource="users", action="write", description="Create/update users"),
        Permission(name="delete_users", resource="users", action="delete", description="Delete users"),
        Permission(name="read_roles", resource="roles", action="read", description="Read roles"),
        Permission(name="write_roles", resource="roles", action="write", description="Create/update roles"),
        Permission(name="delete_roles", resource="roles", action="delete", description="Delete roles"),
        Permission(name="read_audit", resource="audit", action="read", description="Read audit logs"),
    ]
    
    for perm in permissions:
        session.add(perm)
    
    # Create admin role
    role = Role(
        name="admin",
        description="Administrator with full access"
    )
    session.add(role)
    session.commit()
    session.refresh(role)
    
    # Assign all permissions to admin role
    for perm in permissions:
        role_perm = RolePermission(
            role_id=role.id,
            permission_id=perm.id
        )
        session.add(role_perm)
    
    session.commit()
    return role


@pytest.fixture(name="user_role")
def user_role_fixture(session: Session) -> Role:
    """Create a basic user role with limited permissions"""
    # Create limited permissions
    permissions = [
        Permission(name="read_own_profile", resource="profile", action="read", description="Read own profile"),
        Permission(name="update_own_profile", resource="profile", action="update", description="Update own profile"),
    ]
    
    for perm in permissions:
        session.add(perm)
    
    # Create user role
    role = Role(
        name="user",
        description="Basic user with limited access"
    )
    session.add(role)
    session.commit()
    session.refresh(role)
    
    # Assign permissions to user role
    for perm in permissions:
        role_perm = RolePermission(
            role_id=role.id,
            permission_id=perm.id
        )
        session.add(role_perm)
    
    session.commit()
    return role


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(test_user) -> dict:
    """Create authentication headers with valid token"""
    from logic.auth.security import create_access_token
    
    token = create_access_token({"sub": test_user.username})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="admin_headers")
def admin_headers_fixture(admin_user) -> dict:
    """Create authentication headers for admin user"""
    from logic.auth.security import create_access_token
    
    token = create_access_token({"sub": admin_user.username})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="expired_token_headers")
def expired_token_headers_fixture(test_user) -> dict:
    """Create authentication headers with expired token"""
    from datetime import timedelta
    from logic.auth.security import create_access_token
    
    token = create_access_token(
        {"sub": test_user.username},
        expires_delta=timedelta(seconds=-1)
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def reset_database(engine):
    """Reset database before each test"""
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)