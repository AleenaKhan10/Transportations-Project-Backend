# Authentication API Test Suite

Comprehensive test suite for authentication and authorization APIs.

## Setup

1. Install test dependencies:
```bash
pip install -r tests/requirements-test.txt
```

2. Ensure environment variables are set (handled automatically by conftest.py for tests)

## Running Tests

### Run all tests:
```bash
pytest
```

### Run with coverage report:
```bash
pytest --cov=app --cov-report=html
```

### Run specific test file:
```bash
pytest tests/test_auth.py
```

### Run specific test class:
```bash
pytest tests/test_auth.py::TestUserLogin
```

### Run specific test:
```bash
pytest tests/test_auth.py::TestUserLogin::test_login_success
```

### Run tests by marker:
```bash
# Run only auth tests
pytest -m auth

# Run only unit tests
pytest -m unit

# Skip slow tests
pytest -m "not slow"
```

### Run with verbose output:
```bash
pytest -v
```

## Test Coverage

The test suite covers:

### User Registration (TestUserRegistration)
- ✅ Successful user registration
- ✅ Duplicate username validation
- ✅ Duplicate email validation
- ✅ Invalid email format validation
- ✅ Registration with role assignment

### User Login (TestUserLogin)
- ✅ Successful login with username
- ✅ Login with email
- ✅ Invalid password handling
- ✅ Non-existent user handling
- ✅ Inactive user handling
- ✅ Rate limiting

### Token Management (TestTokenManagement)
- ✅ Refresh token success
- ✅ Invalid refresh token handling
- ✅ Logout success
- ✅ Logout without authentication

### Password Management (TestPasswordManagement)
- ✅ Forgot password request
- ✅ Password reset with token
- ✅ Invalid token handling
- ✅ Email enumeration prevention

### User Profile (TestUserProfile)
- ✅ Get current user info
- ✅ Unauthorized access handling
- ✅ User info with roles and permissions

### Two-Factor Authentication (TestTwoFactorAuthentication)
- ⏳ Enable 2FA (pending implementation)
- ⏳ Verify 2FA code (pending implementation)
- ⏳ Disable 2FA (pending implementation)

### Email Verification (TestEmailVerification)
- ⏳ Send verification email (pending implementation)
- ⏳ Verify email with token (pending implementation)

### Security Features (TestSecurityFeatures)
- ✅ Password complexity requirements
- ✅ Session management
- ✅ Audit logging

### Error Handling (TestErrorHandling)
- ✅ Malformed request handling
- ✅ Missing required fields
- ✅ Invalid token format
- ✅ Expired token handling

### Integration Tests (TestAuthenticationFlow)
- ✅ Complete user lifecycle (register → login → refresh → logout)

## Test Fixtures

The test suite uses the following fixtures (defined in conftest.py):

- `session`: Test database session
- `client`: FastAPI test client
- `test_user`: Standard test user
- `admin_user`: Admin user with full permissions
- `inactive_user`: Inactive user for testing access restrictions
- `admin_role`: Admin role with all permissions
- `user_role`: Basic user role with limited permissions
- `auth_headers`: Authentication headers with valid token
- `admin_headers`: Admin authentication headers
- `expired_token_headers`: Headers with expired token

## Test Database

Tests use an in-memory SQLite database that is:
- Created fresh for each test session
- Isolated from production data
- Automatically cleaned up after tests

## Continuous Integration

To run tests in CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pip install -r requirements.txt
    pip install -r tests/requirements-test.txt
    pytest --cov=app --cov-report=xml
    
- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure you're running tests from the app directory
2. **Database errors**: Check that SQLite is available
3. **Token errors**: Verify SECRET_KEY is set in environment

### Debug Mode

Run tests with detailed output:
```bash
pytest -vv --tb=long
```

## Adding New Tests

1. Create test file following naming convention: `test_*.py`
2. Import required fixtures from conftest.py
3. Group related tests in classes
4. Use descriptive test names
5. Add appropriate markers (@pytest.mark.auth, etc.)

## Best Practices

1. Each test should be independent
2. Use fixtures for common setup
3. Test both success and failure cases
4. Include edge cases
5. Mock external dependencies
6. Keep tests fast and focused
7. Use meaningful assertions