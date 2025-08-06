# Backend Requirements Document
## Transportation Centralized Dashboard - Authentication & Admin System

### Overview
This document outlines the complete backend requirements for implementing a comprehensive authentication and admin management system for the Transportation Centralized Dashboard. The system requires role-based access control (RBAC), user management, session management, audit logging, and secure authentication.

## Database Schema Changes

### 1. Users Table
```sql
CREATE TABLE users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    avatar VARCHAR(500),
    status ENUM('active', 'inactive', 'suspended', 'pending') DEFAULT 'pending',
    department VARCHAR(100),
    two_factor_enabled BOOLEAN DEFAULT FALSE,
    two_factor_secret VARCHAR(100),
    email_verified BOOLEAN DEFAULT FALSE,
    email_verification_token VARCHAR(255),
    password_reset_token VARCHAR(255),
    password_reset_expires DATETIME,
    last_login_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by BIGINT,
    FOREIGN KEY (created_by) REFERENCES users(id),
    INDEX idx_email (email),
    INDEX idx_username (username),
    INDEX idx_status (status)
);
```

### 2. Roles Table
```sql
CREATE TABLE roles (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name)
);
```

### 3. Permissions Table
```sql
CREATE TABLE permissions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_permission (resource, action),
    INDEX idx_resource (resource)
);
```

### 4. User Roles Table (Junction)
```sql
CREATE TABLE user_roles (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    assigned_by BIGINT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_by) REFERENCES users(id),
    UNIQUE KEY unique_user_role (user_id, role_id)
);
```

### 5. Role Permissions Table (Junction)
```sql
CREATE TABLE role_permissions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    role_id BIGINT NOT NULL,
    permission_id BIGINT NOT NULL,
    granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE,
    UNIQUE KEY unique_role_permission (role_id, permission_id)
);
```

### 6. User Sessions Table
```sql
CREATE TABLE user_sessions (
    id VARCHAR(255) PRIMARY KEY,
    user_id BIGINT NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_expires_at (expires_at),
    INDEX idx_is_active (is_active)
);
```

### 7. Audit Logs Table
```sql
CREATE TABLE audit_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT,
    user_email VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(100) NOT NULL,
    resource_id VARCHAR(100),
    old_values JSON,
    new_values JSON,
    ip_address VARCHAR(45),
    user_agent TEXT,
    status ENUM('success', 'failure') DEFAULT 'success',
    error_message TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_action (action),
    INDEX idx_resource (resource),
    INDEX idx_timestamp (timestamp),
    INDEX idx_status (status)
);
```

### 8. Default Data Inserts
```sql
-- Default Permissions
INSERT INTO permissions (name, resource, action, description) VALUES
('View Dashboard', 'dashboard', 'view', 'Access main dashboard'),
('Manage Users', 'users', 'manage', 'Create, edit, delete users'),
('View Users', 'users', 'view', 'View user list and details'),
('Manage Roles', 'roles', 'manage', 'Create, edit, delete roles'),
('View Reports', 'reports', 'view', 'Access reporting system'),
('Create Reports', 'reports', 'create', 'Generate new reports'),
('System Settings', 'system', 'manage', 'Modify system configuration'),
('View Audit Logs', 'audit', 'view', 'Access audit trail'),
('Manage Trailers', 'trailers', 'manage', 'Manage trailer information'),
('View Trailers', 'trailers', 'view', 'View trailer data'),
('Manage Drivers', 'drivers', 'manage', 'Manage driver information'),
('View Drivers', 'drivers', 'view', 'View driver data'),
('Manage Alerts', 'alerts', 'manage', 'Configure and manage alerts'),
('View Alerts', 'alerts', 'view', 'View system alerts');

-- Default Roles
INSERT INTO roles (name, description) VALUES
('Super Admin', 'Full system access with all permissions'),
('Manager', 'Department management access'),
('Operator', 'Basic operational access'),
('Viewer', 'Read-only access');

-- Assign permissions to roles
INSERT INTO role_permissions (role_id, permission_id) 
SELECT r.id, p.id FROM roles r, permissions p WHERE r.name = 'Super Admin';

INSERT INTO role_permissions (role_id, permission_id) 
SELECT r.id, p.id FROM roles r, permissions p 
WHERE r.name = 'Manager' AND p.name IN ('View Dashboard', 'Manage Users', 'View Users', 'View Reports', 'Create Reports');

INSERT INTO role_permissions (role_id, permission_id) 
SELECT r.id, p.id FROM roles r, permissions p 
WHERE r.name = 'Operator' AND p.name IN ('View Dashboard', 'View Reports');

INSERT INTO role_permissions (role_id, permission_id) 
SELECT r.id, p.id FROM roles r, permissions p 
WHERE r.name = 'Viewer' AND p.name = 'View Dashboard';
```

## API Endpoints

### Authentication Endpoints

#### 1. POST /auth/login
**Purpose**: User authentication
**Request Body**:
```json
{
  "username": "string",
  "password": "string",
  "grant_type": "password"
}
```
**Response**:
```json
{
  "access_token": "string",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "string",
  "user": {
    "id": "string",
    "username": "string",
    "email": "string",
    "fullName": "string",
    "role": {
      "id": "string",
      "name": "string",
      "permissions": ["string"]
    },
    "permissions": ["string"]
  }
}
```

#### 2. POST /auth/users
**Purpose**: Create new user (registration/admin creation)
**Request Body**:
```json
{
  "username": "string",
  "password": "string",
  "email": "string",
  "fullName": "string",
  "phone": "string",
  "roleId": "string",
  "department": "string"
}
```
**Response**:
```json
{
  "id": "string",
  "username": "string",
  "email": "string",
  "status": "pending"
}
```

#### 3. POST /auth/refresh
**Purpose**: Refresh access token
**Request Body**:
```json
{
  "refresh_token": "string"
}
```

#### 4. POST /auth/logout
**Purpose**: Logout and invalidate session
**Headers**: `Authorization: Bearer <token>`

#### 5. POST /auth/forgot-password
**Purpose**: Initiate password reset
**Request Body**:
```json
{
  "email": "string"
}
```

#### 6. POST /auth/reset-password
**Purpose**: Reset password with token
**Request Body**:
```json
{
  "token": "string",
  "newPassword": "string"
}
```

### User Management Endpoints

#### 7. GET /admin/users
**Purpose**: Get all users with filtering and pagination
**Query Parameters**:
- `page`: number (default: 1)
- `limit`: number (default: 20)
- `search`: string
- `status`: string (active|inactive|suspended|pending)
- `roleId`: string
- `department`: string

**Response**:
```json
{
  "users": [
    {
      "id": "string",
      "username": "string",
      "email": "string",
      "fullName": "string",
      "phone": "string",
      "role": {
        "id": "string",
        "name": "string",
        "description": "string"
      },
      "permissions": ["string"],
      "status": "string",
      "department": "string",
      "lastLoginAt": "string",
      "createdAt": "string",
      "updatedAt": "string",
      "twoFactorEnabled": boolean,
      "emailVerified": boolean
    }
  ],
  "total": number,
  "page": number,
  "limit": number,
  "totalPages": number
}
```

#### 8. GET /admin/users/{id}
**Purpose**: Get user by ID
**Response**: Single user object

#### 9. PUT /admin/users/{id}
**Purpose**: Update user
**Request Body**:
```json
{
  "email": "string",
  "fullName": "string",
  "phone": "string",
  "roleId": "string",
  "department": "string",
  "status": "string"
}
```

#### 10. DELETE /admin/users/{id}
**Purpose**: Delete user

#### 11. POST /admin/users/{id}/suspend
**Purpose**: Suspend user
**Request Body**:
```json
{
  "reason": "string"
}
```

#### 12. POST /admin/users/{id}/activate
**Purpose**: Activate user

#### 13. POST /admin/users/{id}/reset-password
**Purpose**: Admin reset user password
**Response**:
```json
{
  "temporaryPassword": "string"
}
```

#### 14. POST /admin/users/{id}/force-logout
**Purpose**: Force logout user (terminate all sessions)

#### 15. GET /admin/users/stats
**Purpose**: Get user statistics
**Response**:
```json
{
  "totalUsers": number,
  "activeUsers": number,
  "inactiveUsers": number,
  "suspendedUsers": number,
  "pendingUsers": number,
  "totalRoles": number,
  "activeSessions": number,
  "recentLogins": number
}
```

### Role Management Endpoints

#### 16. GET /admin/roles
**Purpose**: Get all roles
**Response**:
```json
[
  {
    "id": "string",
    "name": "string",
    "description": "string",
    "permissions": ["string"],
    "createdAt": "string",
    "updatedAt": "string"
  }
]
```

#### 17. GET /admin/roles/{id}
**Purpose**: Get role by ID

#### 18. POST /admin/roles
**Purpose**: Create new role
**Request Body**:
```json
{
  "name": "string",
  "description": "string",
  "permissions": ["string"]
}
```

#### 19. PUT /admin/roles/{id}
**Purpose**: Update role
**Request Body**:
```json
{
  "name": "string",
  "description": "string",
  "permissions": ["string"]
}
```

#### 20. DELETE /admin/roles/{id}
**Purpose**: Delete role

### Permission Management Endpoints

#### 21. GET /admin/permissions
**Purpose**: Get all permissions
**Response**:
```json
[
  {
    "id": "string",
    "name": "string",
    "resource": "string",
    "action": "string",
    "description": "string"
  }
]
```

#### 22. GET /admin/permissions/resource/{resource}
**Purpose**: Get permissions by resource

### Session Management Endpoints

#### 23. GET /admin/sessions
**Purpose**: Get active sessions
**Query Parameters**:
- `userId`: string
- `page`: number
- `limit`: number

**Response**:
```json
{
  "sessions": [
    {
      "id": "string",
      "userId": "string",
      "userEmail": "string",
      "ipAddress": "string",
      "userAgent": "string",
      "lastActivity": "string",
      "expiresAt": "string",
      "isActive": boolean
    }
  ],
  "total": number
}
```

#### 24. GET /admin/sessions/{id}
**Purpose**: Get session by ID

#### 25. DELETE /admin/sessions/{id}
**Purpose**: Terminate session

#### 26. DELETE /admin/sessions/user/{userId}
**Purpose**: Terminate all user sessions

### Audit Log Endpoints

#### 27. GET /admin/audit-logs
**Purpose**: Get audit logs
**Query Parameters**:
- `userId`: string
- `action`: string
- `resource`: string
- `startDate`: string (ISO 8601)
- `endDate`: string (ISO 8601)
- `page`: number
- `limit`: number

**Response**:
```json
{
  "logs": [
    {
      "id": "string",
      "userId": "string",
      "userEmail": "string",
      "action": "string",
      "resource": "string",
      "resourceId": "string",
      "changes": {
        "old": {},
        "new": {}
      },
      "ipAddress": "string",
      "userAgent": "string",
      "status": "string",
      "errorMessage": "string",
      "timestamp": "string"
    }
  ],
  "total": number
}
```

### Bulk Operations

#### 28. POST /admin/users/bulk-update
**Purpose**: Bulk update users
**Request Body**:
```json
{
  "userIds": ["string"],
  "updates": {
    "status": "string",
    "roleId": "string"
  }
}
```

#### 29. POST /admin/users/bulk-delete
**Purpose**: Bulk delete users
**Request Body**:
```json
{
  "userIds": ["string"]
}
```

### Export/Import Endpoints

#### 30. GET /admin/users/export
**Purpose**: Export users
**Query Parameters**:
- `format`: string (csv|xlsx)
**Response**: File download

#### 31. POST /admin/users/import
**Purpose**: Import users
**Request**: Multipart form data with file
**Response**:
```json
{
  "imported": number,
  "failed": number,
  "errors": ["string"]
}
```

### Two-Factor Authentication

#### 32. POST /admin/users/{id}/2fa/enable
**Purpose**: Enable 2FA for user

#### 33. POST /admin/users/{id}/2fa/disable
**Purpose**: Disable 2FA for user

### Email Verification

#### 34. POST /admin/users/{id}/resend-verification
**Purpose**: Resend verification email

#### 35. POST /admin/users/{id}/mark-verified
**Purpose**: Manually mark email as verified

## Security Requirements

### 1. Authentication & Authorization
- Use JWT tokens for authentication
- Implement refresh token mechanism
- Token expiration: Access token (1 hour), Refresh token (7 days)
- Role-based access control (RBAC) on all admin endpoints
- Middleware to verify permissions for each endpoint

### 2. Password Security
- Hash passwords with bcrypt (cost factor: 12)
- Password requirements: min 8 chars, uppercase, lowercase, number, special char
- Password reset tokens expire in 1 hour
- Rate limiting on login attempts (5 attempts per 15 minutes)

### 3. Session Management
- Track all user sessions
- Automatic session cleanup for expired sessions
- Force logout capability
- Session timeout handling

### 4. Audit Logging
- Log all admin actions (create, update, delete)
- Log authentication events (login, logout, failed attempts)
- Log permission changes
- Include IP address and user agent in logs

### 5. Rate Limiting
- Authentication endpoints: 5 requests per minute per IP
- Password reset: 3 requests per hour per email
- Admin endpoints: 100 requests per minute per user

### 6. Input Validation
- Validate all input data
- Sanitize user inputs
- Validate email formats
- Username validation (alphanumeric, 3-50 chars)

### 7. Error Handling
- Return consistent error responses
- Don't expose sensitive information in error messages
- Log detailed errors for debugging

## Implementation Guidelines

### 1. Middleware Requirements
- Authentication middleware for protected routes
- Permission checking middleware
- Audit logging middleware
- Rate limiting middleware
- Input validation middleware

### 2. Database Considerations
- Use database transactions for multi-table operations
- Implement soft deletes for users (add deleted_at column)
- Regular cleanup of expired sessions and tokens
- Index optimization for performance

### 3. API Response Standards
- Consistent JSON response format
- HTTP status codes: 200 (success), 201 (created), 400 (bad request), 401 (unauthorized), 403 (forbidden), 404 (not found), 500 (server error)
- Pagination for list endpoints
- Include metadata in list responses

### 4. Testing Requirements
- Unit tests for all service functions
- Integration tests for API endpoints
- Security testing for authentication flows
- Load testing for admin endpoints

### 5. Documentation
- OpenAPI/Swagger documentation for all endpoints
- Database schema documentation
- Setup and deployment instructions

## Performance Considerations

### 1. Database Optimization
- Proper indexing on frequently queried columns
- Connection pooling
- Query optimization
- Consider read replicas for heavy read operations

### 2. Caching Strategy
- Cache user permissions and roles
- Cache session data
- Redis for session storage and caching

### 3. Monitoring
- API response times monitoring
- Database query performance
- Error rate tracking
- User activity monitoring

## Deployment Requirements

### 1. Environment Variables
```env
DATABASE_URL=mysql://user:password@host:port/database
JWT_SECRET=random-secret-key
JWT_REFRESH_SECRET=random-refresh-secret-key
REDIS_URL=redis://host:port
SMTP_HOST=smtp.server.com
SMTP_PORT=587
SMTP_USER=email@domain.com
SMTP_PASSWORD=password
ADMIN_EMAIL=admin@agylogistics.com
```

### 2. Production Considerations
- SSL/TLS encryption
- Secure headers (CORS, CSP, etc.)
- Environment-specific configurations
- Database migrations
- Backup strategies
- Monitoring and alerting setup

This comprehensive backend requirements document provides all necessary details for implementing the complete authentication and admin management system. The implementation should follow REST API best practices, security guidelines, and include proper error handling, validation, and logging throughout.