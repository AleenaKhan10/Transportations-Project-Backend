-- Database Setup Script for Authentication and Admin Management System
-- Run this script to create all required tables and insert default data

-- Drop existing tables if they exist (in correct order to handle foreign keys)
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS user_sessions;
DROP TABLE IF EXISTS role_permissions;
DROP TABLE IF EXISTS user_roles;
DROP TABLE IF EXISTS permissions;
DROP TABLE IF EXISTS roles;
DROP TABLE IF EXISTS users;

-- 1. Users Table
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

-- 2. Roles Table
CREATE TABLE roles (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name)
);

-- 3. Permissions Table
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

-- 4. User Roles Table (Junction)
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

-- 5. Role Permissions Table (Junction)
CREATE TABLE role_permissions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    role_id BIGINT NOT NULL,
    permission_id BIGINT NOT NULL,
    granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE,
    UNIQUE KEY unique_role_permission (role_id, permission_id)
);

-- 6. User Sessions Table
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

-- 7. Audit Logs Table
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

-- Insert Default Data

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
-- Super Admin gets all permissions
INSERT INTO role_permissions (role_id, permission_id) 
SELECT r.id, p.id FROM roles r, permissions p WHERE r.name = 'Super Admin';

-- Manager gets specific permissions
INSERT INTO role_permissions (role_id, permission_id) 
SELECT r.id, p.id FROM roles r, permissions p 
WHERE r.name = 'Manager' AND p.name IN (
    'View Dashboard', 'Manage Users', 'View Users', 'View Reports', 'Create Reports',
    'View Trailers', 'View Drivers', 'View Alerts'
);

-- Operator gets operational permissions
INSERT INTO role_permissions (role_id, permission_id) 
SELECT r.id, p.id FROM roles r, permissions p 
WHERE r.name = 'Operator' AND p.name IN ('View Dashboard', 'View Reports', 'View Trailers', 'View Drivers', 'View Alerts');

-- Viewer gets read-only access
INSERT INTO role_permissions (role_id, permission_id) 
SELECT r.id, p.id FROM roles r, permissions p 
WHERE r.name = 'Viewer' AND p.name IN ('View Dashboard', 'View Reports', 'View Trailers', 'View Drivers');

-- Create default Super Admin user (password: admin123)
-- Note: In production, change this password immediately
INSERT INTO users (username, email, password_hash, full_name, status, email_verified) VALUES
('admin', 'admin@agylogistics.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBdgkCOxhD9d7u', 'System Administrator', 'active', TRUE);

-- Assign Super Admin role to the default admin user
INSERT INTO user_roles (user_id, role_id) 
SELECT u.id, r.id FROM users u, roles r 
WHERE u.username = 'admin' AND r.name = 'Super Admin';

-- Display successful completion message
SELECT 'Database setup completed successfully!' as message;