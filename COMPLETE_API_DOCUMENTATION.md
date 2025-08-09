# 🔐 AGY Intelligence Hub - Complete API Documentation

## 🎯 System Overview
The AGY Intelligence Hub is a comprehensive backend system built with FastAPI featuring:
- JWT-based authentication with role-based access control
- Complete user and admin management
- Session tracking and audit logging
- Real-time alert management
- Driver and trailer management
- Trip reporting and analytics

**Base URL**: `http://localhost:8000`

---

## 🔑 Authentication Endpoints

### 1. Login User
**Endpoint**: `POST /auth/login`  
**Authentication**: None (Public)  
**Purpose**: Authenticate user and receive JWT tokens with complete user profile

**Request Headers**:
```
Content-Type: application/x-www-form-urlencoded
```

**Request Body**:
```
username=admin@agelogistics.com&password=admin123
```

**Success Response (200)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 2,
    "username": "admin@agelogistics.com",
    "email": "admin@agelogistics.com",
    "fullName": "System Administrator",
    "role": {
      "id": 1,
      "name": "Super Admin",
      "slug": "super_admin",
      "description": "Full system access with all permissions"
    },
    "permissions": [
      {
        "id": 1,
        "name": "View Dashboard",
        "slug": "view_dashboard",
        "resource": "dashboard",
        "action": "view"
      },
      {
        "id": 2,
        "name": "Manage Users",
        "slug": "manage_users",
        "resource": "users",
        "action": "manage"
      }
    ],
    "status": "active",
    "is_active": true
  }
}
```

**Error Response (401)**:
```json
{
  "detail": "Incorrect username or password"
}
```

---

### 2. Get Current User
**Endpoint**: `GET /auth/me`  
**Authentication**: Required (Bearer Token)  
**Purpose**: Get current authenticated user's information

**Request Headers**:
```
Authorization: Bearer {access_token}
```

**Success Response (200)**:
```json
{
  "id": 2,
  "username": "admin@agelogistics.com",
  "email": "admin@agelogistics.com",
  "fullName": "System Administrator",
  "role": {
    "id": 1,
    "name": "Super Admin",
    "slug": "super_admin",
    "description": "Full system access with all permissions"
  },
  "permissions": [...],
  "status": "active",
  "is_active": true
}
```

---

### 3. Refresh Token
**Endpoint**: `POST /auth/refresh`  
**Authentication**: None (Uses refresh token)  
**Purpose**: Get new access token using refresh token

**Query Parameters**:
- `refresh_token` (string, required): The refresh token

**Success Response (200)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 1800
}
```

**Error Response (401)**:
```json
{
  "detail": "Invalid refresh token"
}
```

---

### 4. Logout User
**Endpoint**: `POST /auth/logout`  
**Authentication**: Required (Bearer Token)  
**Purpose**: Logout current user

**Request Headers**:
```
Authorization: Bearer {access_token}
```

**Success Response (200)**:
```json
{
  "message": "Successfully logged out"
}
```

---

### 5. Register User (Public)
**Endpoint**: `POST /auth/register`  
**Authentication**: None (Public)  
**Purpose**: Public registration endpoint for testing

**Request Headers**:
```
Content-Type: application/json
```

**Request Body**:
```json
{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "password123",
  "full_name": "New User"
}
```

**Success Response (200)**:
```json
{
  "id": 10,
  "username": "newuser",
  "email": "newuser@example.com",
  "fullName": "New User",
  "role": null,
  "permissions": [],
  "status": "active",
  "is_active": true
}
```

---

### 6. Create User (Admin)
**Endpoint**: `POST /auth/users`  
**Authentication**: Required (Admin Token)  
**Purpose**: Admin endpoint to create new users

**Request Headers**:
```
Authorization: Bearer {admin_access_token}
Content-Type: application/json
```

**Request Body**:
```json
{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "password123",
  "full_name": "New User",
  "status": "active",
  "role_id": 3
}
```

**Success Response (200)**: Same as register endpoint

---

### 7. Forgot Password
**Endpoint**: `POST /auth/forgot-password`  
**Authentication**: None (Public)  
**Purpose**: Request password reset

**Query Parameters**:
- `email` (string, required): User email

**Success Response (200)**:
```json
{
  "message": "If the email exists, a reset link has been sent"
}
```

---

### 8. Reset Password
**Endpoint**: `POST /auth/reset-password`  
**Authentication**: None (Uses reset token)  
**Purpose**: Reset password with token

**Query Parameters**:
- `token` (string, required): Reset token
- `new_password` (string, required): New password

**Success Response (200)**:
```json
{
  "message": "Password reset successfully"
}
```

---

## 👥 Admin User Management Endpoints

### 1. Get All Users
**Endpoint**: `GET /admin/users`  
**Authentication**: Required (Admin Token)  
**Purpose**: Get paginated list of users with filtering

**Request Headers**:
```
Authorization: Bearer {admin_token}
```

**Query Parameters**:
- `page` (int, optional, default: 1): Page number
- `limit` (int, optional, default: 20, max: 100): Items per page
- `search` (string, optional): Search users by username/email/name
- `status` (string, optional): Filter by status (active|inactive|suspended|pending)
- `role_id` (int, optional): Filter by role ID
- `department` (string, optional): Filter by department

**Success Response (200)**:
```json
{
  "items": [
    {
      "id": 1,
      "username": "user1",
      "email": "user1@example.com",
      "fullName": "User One",
      "role": {
        "id": 2,
        "name": "Manager",
        "slug": "manager"
      },
      "status": "active",
      "department": "Operations",
      "created_at": "2024-01-01T00:00:00",
      "last_login_at": "2024-01-10T00:00:00"
    }
  ],
  "total": 50,
  "page": 1,
  "limit": 20,
  "pages": 3
}
```

---

### 2. Get User by ID
**Endpoint**: `GET /admin/users/{user_id}`  
**Authentication**: Required (Admin Token)  
**Purpose**: Get specific user details

**Path Parameters**:
- `user_id` (int, required): User ID

**Request Headers**:
```
Authorization: Bearer {admin_token}
```

**Success Response (200)**: Full user object with role and permissions

---

### 3. Update User
**Endpoint**: `PUT /admin/users/{user_id}`  
**Authentication**: Required (Admin Token)  
**Purpose**: Update user information

**Path Parameters**:
- `user_id` (int, required): User ID

**Request Headers**:
```
Authorization: Bearer {admin_token}
Content-Type: application/json
```

**Request Body**:
```json
{
  "email": "newemail@example.com",
  "full_name": "Updated Name",
  "status": "active",
  "role_id": 2,
  "department": "Engineering"
}
```

**Success Response (200)**: Updated user object

---

### 4. Delete User
**Endpoint**: `DELETE /admin/users/{user_id}`  
**Authentication**: Required (Admin Token)  
**Purpose**: Delete a user

**Path Parameters**:
- `user_id` (int, required): User ID

**Request Headers**:
```
Authorization: Bearer {admin_token}
```

**Success Response (200)**:
```json
{
  "message": "User deleted successfully"
}
```

---

### 5. Suspend User
**Endpoint**: `POST /admin/users/{user_id}/suspend`  
**Authentication**: Required (Admin Token)  
**Purpose**: Suspend a user account

**Path Parameters**:
- `user_id` (int, required): User ID

**Query Parameters**:
- `reason` (string, optional): Reason for suspension

**Request Headers**:
```
Authorization: Bearer {admin_token}
```

**Success Response (200)**:
```json
{
  "message": "User suspended successfully"
}
```

---

### 6. Activate User
**Endpoint**: `POST /admin/users/{user_id}/activate`  
**Authentication**: Required (Admin Token)  
**Purpose**: Activate a suspended/inactive user

**Path Parameters**:
- `user_id` (int, required): User ID

**Request Headers**:
```
Authorization: Bearer {admin_token}
```

**Success Response (200)**:
```json
{
  "message": "User activated successfully"
}
```

---

### 7. Admin Reset User Password
**Endpoint**: `POST /admin/users/{user_id}/reset-password`  
**Authentication**: Required (Admin Token)  
**Purpose**: Admin forcefully resets user password

**Path Parameters**:
- `user_id` (int, required): User ID

**Request Headers**:
```
Authorization: Bearer {admin_token}
```

**Success Response (200)**:
```json
{
  "message": "Password reset successfully",
  "temporary_password": "TempPass123!"
}
```

---

### 8. Force Logout User
**Endpoint**: `POST /admin/users/{user_id}/force-logout`  
**Authentication**: Required (Admin Token)  
**Purpose**: Terminate all user sessions

**Path Parameters**:
- `user_id` (int, required): User ID

**Request Headers**:
```
Authorization: Bearer {admin_token}
```

**Success Response (200)**:
```json
{
  "message": "User sessions terminated",
  "sessions_terminated": 3
}
```

---

### 9. Get User Statistics
**Endpoint**: `GET /admin/users/stats`  
**Authentication**: Required (Admin Token)  
**Purpose**: Get overall user statistics

**Request Headers**:
```
Authorization: Bearer {admin_token}
```

**Success Response (200)**:
```json
{
  "total_users": 150,
  "active_users": 120,
  "inactive_users": 20,
  "suspended_users": 10,
  "pending_users": 0,
  "total_roles": 5,
  "active_sessions": 45,
  "recent_logins": 23
}
```

---

### 10. Bulk Update Users
**Endpoint**: `POST /admin/users/bulk-update`  
**Authentication**: Required (Admin Token)  
**Purpose**: Update multiple users at once

**Request Headers**:
```
Authorization: Bearer {admin_token}
Content-Type: application/json
```

**Request Body**:
```json
{
  "user_ids": [1, 2, 3],
  "updates": {
    "status": "active",
    "department": "Operations"
  }
}
```

**Success Response (200)**:
```json
{
  "message": "3 users updated successfully"
}
```

---

### 11. Bulk Delete Users
**Endpoint**: `POST /admin/users/bulk-delete`  
**Authentication**: Required (Admin Token)  
**Purpose**: Delete multiple users

**Request Headers**:
```
Authorization: Bearer {admin_token}
Content-Type: application/json
```

**Request Body**:
```json
[1, 2, 3, 4, 5]
```

**Success Response (200)**:
```json
{
  "message": "5 users deleted successfully"
}
```

---

## 🛡️ Admin Role Management Endpoints

### 1. Get All Roles
**Endpoint**: `GET /admin/roles`  
**Authentication**: Required (Admin Token)  
**Purpose**: Get all roles in the system

**Request Headers**:
```
Authorization: Bearer {admin_token}
```

**Success Response (200)**:
```json
[
  {
    "id": 1,
    "name": "Super Admin",
    "slug": "super_admin",
    "description": "Full system access",
    "level": 100,
    "user_count": 1,
    "permission_count": 25
  }
]
```

---

### 2. Get Role by ID
**Endpoint**: `GET /admin/roles/{role_id}`  
**Authentication**: Required (Admin Token)  
**Purpose**: Get specific role with permissions

**Path Parameters**:
- `role_id` (int, required): Role ID

**Request Headers**:
```
Authorization: Bearer {admin_token}
```

**Success Response (200)**:
```json
{
  "id": 1,
  "name": "Super Admin",
  "slug": "super_admin",
  "description": "Full system access",
  "level": 100,
  "permissions": [
    {
      "id": 1,
      "name": "View Dashboard",
      "slug": "view_dashboard",
      "resource": "dashboard",
      "action": "view"
    }
  ],
  "users": [
    {
      "id": 2,
      "username": "admin@agelogistics.com",
      "email": "admin@agelogistics.com"
    }
  ]
}
```

---

### 3. Create Role
**Endpoint**: `POST /admin/roles`  
**Authentication**: Required (Admin Token)  
**Purpose**: Create new role

**Request Headers**:
```
Authorization: Bearer {admin_token}
Content-Type: application/json
```

**Request Body**:
```json
{
  "name": "Custom Role",
  "slug": "custom_role",
  "description": "Custom role for special users",
  "level": 50,
  "permission_ids": [1, 2, 3, 4]
}
```

**Success Response (200)**: Created role object

---

### 4. Update Role
**Endpoint**: `PUT /admin/roles/{role_id}`  
**Authentication**: Required (Admin Token)  
**Purpose**: Update role information and permissions

**Path Parameters**:
- `role_id` (int, required): Role ID

**Request Headers**:
```
Authorization: Bearer {admin_token}
Content-Type: application/json
```

**Request Body**:
```json
{
  "name": "Updated Role Name",
  "description": "Updated description",
  "permission_ids": [1, 2, 3, 4, 5]
}
```

**Success Response (200)**: Updated role object

---

### 5. Delete Role
**Endpoint**: `DELETE /admin/roles/{role_id}`  
**Authentication**: Required (Admin Token)  
**Purpose**: Delete a role (users with this role will lose it)

**Path Parameters**:
- `role_id` (int, required): Role ID

**Request Headers**:
```
Authorization: Bearer {admin_token}
```

**Success Response (200)**:
```json
{
  "message": "Role deleted successfully"
}
```

---

## 🔐 Admin Permission Management Endpoints

### 1. Get All Permissions
**Endpoint**: `GET /admin/permissions`  
**Authentication**: Required (Admin Token)  
**Purpose**: Get all available permissions

**Request Headers**:
```
Authorization: Bearer {admin_token}
```

**Success Response (200)**:
```json
[
  {
    "id": 1,
    "name": "View Dashboard",
    "slug": "view_dashboard",
    "resource": "dashboard",
    "action": "view",
    "description": "Access to main dashboard"
  }
]
```

---

### 2. Get Permissions by Resource
**Endpoint**: `GET /admin/permissions/resource/{resource}`  
**Authentication**: Required (Admin Token)  
**Purpose**: Get all permissions for a specific resource

**Path Parameters**:
- `resource` (string, required): Resource name

**Request Headers**:
```
Authorization: Bearer {admin_token}
```

**Success Response (200)**: Array of permissions for that resource

---

### 3. Create Permission
**Endpoint**: `POST /admin/permissions`  
**Authentication**: Required (Admin Token)  
**Purpose**: Create new permission

**Request Headers**:
```
Authorization: Bearer {admin_token}
Content-Type: application/json
```

**Request Body**:
```json
{
  "name": "New Permission",
  "slug": "new_permission",
  "resource": "custom_resource",
  "action": "manage",
  "description": "New custom permission"
}
```

**Success Response (200)**: Created permission object

---

## 📊 Admin Session Management Endpoints

### 1. Get All Sessions
**Endpoint**: `GET /admin/sessions`  
**Authentication**: Required (Admin Token)  
**Purpose**: View all active user sessions

**Request Headers**:
```
Authorization: Bearer {admin_token}
```

**Query Parameters**:
- `user_id` (int, optional): Filter by user ID
- `active_only` (boolean, optional, default: true): Show only active sessions

**Success Response (200)**:
```json
[
  {
    "id": "session-uuid",
    "user_id": 2,
    "username": "admin@agelogistics.com",
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0...",
    "last_activity": "2024-01-10T10:00:00",
    "expires_at": "2024-01-10T11:00:00",
    "is_active": true
  }
]
```

---

### 2. Terminate Session
**Endpoint**: `DELETE /admin/sessions/{session_id}`  
**Authentication**: Required (Admin Token)  
**Purpose**: Force terminate a specific session

**Path Parameters**:
- `session_id` (string, required): Session ID

**Request Headers**:
```
Authorization: Bearer {admin_token}
```

**Success Response (200)**:
```json
{
  "message": "Session terminated successfully"
}
```

---

### 3. Cleanup Expired Sessions
**Endpoint**: `POST /admin/sessions/cleanup`  
**Authentication**: Required (Admin Token)  
**Purpose**: Remove all expired sessions from database

**Request Headers**:
```
Authorization: Bearer {admin_token}
```

**Success Response (200)**:
```json
{
  "message": "Cleanup completed",
  "sessions_removed": 15
}
```

---

## 📝 Admin Audit Log Endpoints

### 1. Get Audit Logs
**Endpoint**: `GET /admin/audit`  
**Authentication**: Required (Admin Token)  
**Purpose**: View system audit trail

**Request Headers**:
```
Authorization: Bearer {admin_token}
```

**Query Parameters**:
- `page` (int, optional, default: 1): Page number
- `limit` (int, optional, default: 50): Items per page
- `user_id` (int, optional): Filter by user ID
- `action` (string, optional): Filter by action
- `resource` (string, optional): Filter by resource
- `status` (string, optional): Filter by status (success|failure)
- `from_date` (string, optional): Start date (ISO format)
- `to_date` (string, optional): End date (ISO format)

**Success Response (200)**:
```json
{
  "items": [
    {
      "id": 1,
      "user_id": 2,
      "user_email": "admin@agelogistics.com",
      "action": "login",
      "resource": "auth",
      "resource_id": null,
      "ip_address": "192.168.1.1",
      "status": "success",
      "timestamp": "2024-01-10T10:00:00"
    }
  ],
  "total": 1000,
  "page": 1,
  "limit": 50
}
```

---

### 2. Get Audit Log by ID
**Endpoint**: `GET /admin/audit/{log_id}`  
**Authentication**: Required (Admin Token)  
**Purpose**: Get detailed audit log entry

**Path Parameters**:
- `log_id` (int, required): Audit log ID

**Request Headers**:
```
Authorization: Bearer {admin_token}
```

**Success Response (200)**: Full audit log entry with old/new values

---

### 3. Export Audit Logs
**Endpoint**: `POST /admin/audit/export`  
**Authentication**: Required (Admin Token)  
**Purpose**: Export audit logs to CSV/Excel

**Request Headers**:
```
Authorization: Bearer {admin_token}
Content-Type: application/json
```

**Request Body**:
```json
{
  "format": "csv",
  "filters": {
    "from_date": "2024-01-01",
    "to_date": "2024-01-31",
    "resource": "users"
  }
}
```

**Success Response (200)**: File download or URL to download

---

## 📤 Admin Data Export Endpoints

### 1. Export Users
**Endpoint**: `POST /admin/export/users`  
**Authentication**: Required (Admin Token)  
**Purpose**: Export user data

**Request Headers**:
```
Authorization: Bearer {admin_token}
Content-Type: application/json
```

**Request Body**:
```json
{
  "format": "csv",
  "include_roles": true,
  "include_permissions": false
}
```

**Success Response (200)**: File download

---

### 2. Export Sessions
**Endpoint**: `POST /admin/export/sessions`  
**Authentication**: Required (Admin Token)  
**Purpose**: Export session data

**Request Headers**:
```
Authorization: Bearer {admin_token}
```

**Success Response (200)**: File download

---

## 🚨 Alert Management Endpoints

### 1. Get Alert Filters
**Endpoint**: `GET /alerts/filters/`  
**Authentication**: Required (Bearer Token)  
**Purpose**: Get all alert filters

**Request Headers**:
```
Authorization: Bearer {access_token}
```

**Success Response (200)**: Array of alert filter objects

---

### 2. Create Alert Filter
**Endpoint**: `POST /alerts/filters/`  
**Authentication**: Required (Bearer Token)  
**Purpose**: Create new alert filter

**Request Headers**:
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body**: Alert filter configuration object

---

### 3. Get Alert Filter by ID
**Endpoint**: `GET /alerts/filters/{filter_id}`  
**Authentication**: Required (Bearer Token)  
**Purpose**: Get specific alert filter

**Path Parameters**:
- `filter_id` (int, required): Filter ID

---

### 4. Update Alert Filter
**Endpoint**: `PUT /alerts/filters/{filter_id}`  
**Authentication**: Required (Bearer Token)  
**Purpose**: Update alert filter

**Path Parameters**:
- `filter_id` (int, required): Filter ID

---

### 5. Delete Alert Filter
**Endpoint**: `DELETE /alerts/filters/{filter_id}`  
**Authentication**: Required (Bearer Token)  
**Purpose**: Delete alert filter

**Path Parameters**:
- `filter_id` (int, required): Filter ID

---

## 🚛 Driver Management Endpoints

### 1. Get All Drivers
**Endpoint**: `GET /drivers/raw`  
**Authentication**: Required (Bearer Token)  
**Purpose**: Get all drivers

**Request Headers**:
```
Authorization: Bearer {access_token}
```

**Success Response (200)**: Array of driver objects

---

### 2. Get Driver by ID
**Endpoint**: `GET /drivers/raw/{driver_id}`  
**Authentication**: Required (Bearer Token)  
**Purpose**: Get specific driver

**Path Parameters**:
- `driver_id` (int, required): Driver ID

---

### 3. Configure Driver Call Settings
**Endpoint**: `POST /drivers/settings/call/bulk`  
**Authentication**: Required (Bearer Token)  
**Purpose**: Configure driver call settings in bulk

**Request Headers**:
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body**: Bulk driver call configuration

---

## 🚚 Trip Management Endpoints

### 1. Get Trailer Trips
**Endpoint**: `GET /trips/trailers`  
**Authentication**: Required (Bearer Token)  
**Purpose**: Get all trailer trips

**Request Headers**:
```
Authorization: Bearer {access_token}
```

---

### 2. Get Specific Trip Data
**Endpoint**: `GET /trips/{trip_id}/trailers/{trailer_id}`  
**Authentication**: Required (Bearer Token)  
**Purpose**: Get specific trip data for trailer

**Path Parameters**:
- `trip_id` (int, required): Trip ID
- `trailer_id` (int, required): Trailer ID

---

### 3. Get Latest Alerts
**Endpoint**: `GET /trips/alerts`  
**Authentication**: Required (Bearer Token)  
**Purpose**: Get latest trip alerts

---

## 📊 Reporting Endpoints

### 1. Get Driver Reports
**Endpoint**: `GET /api/driver-reports`  
**Authentication**: Required (Bearer Token)  
**Purpose**: Get driver reports

**Request Headers**:
```
Authorization: Bearer {access_token}
```

---

### 2. Get Morning Reports
**Endpoint**: `GET /api/morning-reports`  
**Authentication**: Required (Bearer Token)  
**Purpose**: Get morning reports

---

## 📞 VAPI Integration Endpoints

### 1. Make VAPI Call
**Endpoint**: `POST /api/vapi-call/{driver_id}`  
**Authentication**: Required (Bearer Token)  
**Purpose**: Make VAPI call to specific driver

**Path Parameters**:
- `driver_id` (int, required): Driver ID

---

### 2. Batch VAPI Calls
**Endpoint**: `POST /api/vapi-calls/batch`  
**Authentication**: Required (Bearer Token)  
**Purpose**: Make batch VAPI calls

---

## 🔗 Webhooks & Integration Endpoints

### 1. Send Muted Entities to Slack
**Endpoint**: `GET /webhook/alerts/slack/muted`  
**Authentication**: Required (Bearer Token)  
**Purpose**: Send muted entities to Slack

---

### 2. Mute Entity Alerts
**Endpoint**: `GET /webhook/alerts/{mute_type}/{entity_id}`  
**Authentication**: Required (Bearer Token)  
**Purpose**: Mute alerts for specific entity

**Path Parameters**:
- `mute_type` (string, required): Type of mute
- `entity_id` (int, required): Entity ID

---

### 3. Slack Interactive Endpoint
**Endpoint**: `POST /slack/interactions`  
**Authentication**: Special (Slack verification)  
**Purpose**: Handle Slack interactive components

---

## 🔒 Permission System

### Available Permissions (25 total):

#### Dashboard Permissions:
- `view_dashboard` - Access to main dashboard

#### User Management:
- `manage_users` - Full user management
- `view_users` - View user information
- `create_users` - Create new users
- `update_users` - Update user information
- `delete_users` - Delete users
- `suspend_users` - Suspend/activate users

#### Role & Permission Management:
- `manage_roles` - Full role management
- `view_roles` - View roles
- `manage_permissions` - Manage permissions

#### System Management:
- `system_settings` - System configuration
- `manage_sessions` - Session management
- `view_audit_logs` - View audit logs
- `export_data` - Export system data

#### Business Operations:
- `manage_drivers` - Driver management
- `view_drivers` - View driver information
- `manage_trailers` - Trailer management
- `view_trailers` - View trailer information
- `manage_alerts` - Alert management
- `view_alerts` - View alerts
- `manage_reports` - Report management
- `view_reports` - View reports
- `manage_trips` - Trip management
- `view_trips` - View trip information

### Default Roles:

1. **Super Admin** (`super_admin`) - All 25 permissions
2. **Admin** (`admin`) - Most permissions except system settings
3. **Manager** (`manager`) - Management and view permissions
4. **Operator** (`operator`) - Operational permissions
5. **Viewer** (`viewer`) - Read-only permissions

---

## 🔐 Authentication & Authorization

### Token Information:
- **Access Token**: Expires in 30 minutes (1800 seconds)
- **Refresh Token**: Expires in 7 days
- **Token Type**: Bearer JWT

### Default Admin Credentials:
- **Username**: `admin@agelogistics.com`
- **Password**: `admin123`
- **Role**: Super Admin (all permissions)

### Frontend Integration:

#### 1. Login Flow:
```javascript
const login = async (username, password) => {
  const formData = new FormData();
  formData.append('username', username);
  formData.append('password', password);
  
  const response = await fetch('/auth/login', {
    method: 'POST',
    body: formData
  });
  
  const data = await response.json();
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('refresh_token', data.refresh_token);
  localStorage.setItem('user', JSON.stringify(data.user));
  
  return data;
};
```

#### 2. Authenticated Requests:
```javascript
const apiCall = async (url, options = {}) => {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...options.headers
    }
  });
  
  if (response.status === 401) {
    await refreshToken();
    return apiCall(url, options);
  }
  
  return response.json();
};
```

#### 3. Permission Checking:
```javascript
const hasPermission = (permissionSlug) => {
  const user = JSON.parse(localStorage.getItem('user'));
  return user?.permissions?.some(p => p.slug === permissionSlug);
};

const hasRole = (roleSlug) => {
  const user = JSON.parse(localStorage.getItem('user'));
  return user?.role?.slug === roleSlug;
};
```

#### 4. Admin Access Check:
```javascript
const isAdmin = () => {
  const user = JSON.parse(localStorage.getItem('user'));
  const adminRoles = ['super_admin', 'admin', 'manager'];
  return adminRoles.includes(user?.role?.slug);
};
```

---

## 🚀 Quick Start for Frontend

### 1. Authentication Setup:
1. Implement login form with username/password
2. Store JWT tokens in localStorage
3. Add Authorization header to all API requests
4. Handle 401 responses with token refresh

### 2. Admin Panel Access:
1. Check user role: `super_admin`, `admin`, or `manager`
2. Show/hide UI based on permissions
3. Use permission slugs for granular access control

### 3. API Error Handling:
- **401**: Token expired, refresh and retry
- **403**: Insufficient permissions
- **400**: Bad request/validation error
- **404**: Resource not found
- **500**: Server error

### 4. Common HTTP Status Codes:
- **200**: Success
- **201**: Created
- **204**: No Content (successful delete)
- **400**: Bad Request
- **401**: Unauthorized
- **403**: Forbidden
- **404**: Not Found
- **422**: Validation Error
- **500**: Internal Server Error

---

## 📋 System Status

### ✅ Fully Implemented:
- Complete authentication system
- User management (CRUD operations)
- Role and permission system
- JWT token management
- Admin management endpoints
- Audit logging capability
- Session management
- Data export endpoints

### ⚠️ Needs Implementation:
- Email notifications
- Password reset token storage
- Real-time session tracking
- Advanced audit filters
- File upload endpoints

### 🔧 Production Considerations:
- Enable rate limiting
- Implement proper CORS
- Add input validation
- Enable audit logging
- Implement 2FA
- Add email verification
- Set up SSL/HTTPS
- Configure database connection pooling

This documentation provides complete coverage of all available endpoints in the AGY Intelligence Hub backend system.