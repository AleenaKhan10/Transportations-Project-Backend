#!/usr/bin/env python3
"""
Database setup script for AGY Intelligence Hub
This script creates all required tables and inserts default data
"""

import sys
import os
from sqlmodel import Session, select
from datetime import datetime

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.database import engine
from models.user import (
    User, Role, Permission, UserRole, RolePermission, 
    UserStatus, UserCreate
)
from logic.auth.service import UserService

def create_default_permissions():
    """Create default permissions"""
    default_permissions = [
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
        ('View Alerts', 'alerts', 'view', 'View system alerts'),
    ]
    
    with Session(engine) as session:
        for name, resource, action, description in default_permissions:
            # Check if permission already exists
            existing = session.exec(
                select(Permission).where(
                    Permission.resource == resource, 
                    Permission.action == action
                )
            ).first()
            
            if not existing:
                permission = Permission(
                    name=name,
                    resource=resource,
                    action=action,
                    description=description
                )
                session.add(permission)
        
        session.commit()
        print("✓ Default permissions created")

def create_default_roles():
    """Create default roles"""
    default_roles = [
        ('Super Admin', 'Full system access with all permissions'),
        ('Manager', 'Department management access'),
        ('Operator', 'Basic operational access'),
        ('Viewer', 'Read-only access'),
    ]
    
    with Session(engine) as session:
        created_roles = {}
        
        for name, description in default_roles:
            # Check if role already exists
            existing = session.exec(select(Role).where(Role.name == name)).first()
            
            if not existing:
                role = Role(name=name, description=description)
                session.add(role)
                session.commit()
                session.refresh(role)
                created_roles[name] = role
                print(f"✓ Created role: {name}")
            else:
                created_roles[name] = existing
                print(f"- Role already exists: {name}")
        
        return created_roles

def assign_permissions_to_roles():
    """Assign permissions to roles"""
    with Session(engine) as session:
        # Get all roles and permissions
        roles = {r.name: r for r in session.exec(select(Role)).all()}
        permissions = {p.name: p for p in session.exec(select(Permission)).all()}
        
        # Define role-permission mappings
        role_permissions = {
            'Super Admin': list(permissions.keys()),  # All permissions
            'Manager': [
                'View Dashboard', 'Manage Users', 'View Users', 'View Reports', 
                'Create Reports', 'View Trailers', 'View Drivers', 'View Alerts'
            ],
            'Operator': [
                'View Dashboard', 'View Reports', 'View Trailers', 
                'View Drivers', 'View Alerts'
            ],
            'Viewer': [
                'View Dashboard', 'View Reports', 'View Trailers', 'View Drivers'
            ]
        }
        
        for role_name, perm_names in role_permissions.items():
            if role_name not in roles:
                continue
                
            role = roles[role_name]
            
            # Remove existing permissions for this role
            existing_perms = session.exec(
                select(RolePermission).where(RolePermission.role_id == role.id)
            ).all()
            for rp in existing_perms:
                session.delete(rp)
            
            # Add new permissions
            for perm_name in perm_names:
                if perm_name in permissions:
                    role_perm = RolePermission(
                        role_id=role.id,
                        permission_id=permissions[perm_name].id
                    )
                    session.add(role_perm)
            
            session.commit()
            print(f"✓ Assigned {len(perm_names)} permissions to {role_name}")

def create_default_admin_user():
    """Create default admin user"""
    with Session(engine) as session:
        # Check if admin user already exists
        existing_admin = session.exec(
            select(User).where(User.username == 'admin')
        ).first()
        
        if existing_admin:
            print("- Admin user already exists")
            return existing_admin
        
        # Create admin user
        admin_data = UserCreate(
            username='admin',
            email='admin@agylogistics.com',
            password='admin123',  # Change this in production!
            full_name='System Administrator',
            status=UserStatus.ACTIVE
        )
        
        admin_user = UserService.create_user(admin_data)
        
        # Assign Super Admin role
        super_admin_role = session.exec(
            select(Role).where(Role.name == 'Super Admin')
        ).first()
        
        if super_admin_role:
            UserService.assign_role_to_user(admin_user.id, super_admin_role.id)
            print("✓ Created admin user with Super Admin role")
        else:
            print("⚠ Admin user created but Super Admin role not found")
        
        # Mark email as verified
        admin_user.email_verified = True
        session.add(admin_user)
        session.commit()
        
        return admin_user

def main():
    """Main setup function"""
    print("🚀 Starting AGY Intelligence Hub database setup...")
    print(f"Database URL: {engine.url}")
    
    try:
        # Create all tables
        from sqlmodel import SQLModel
        SQLModel.metadata.create_all(engine)
        print("✓ Database tables created")
        
        # Create default data
        create_default_permissions()
        roles = create_default_roles()
        assign_permissions_to_roles()
        admin_user = create_default_admin_user()
        
        print("\n🎉 Database setup completed successfully!")
        print("\nDefault admin credentials:")
        print("Username: admin")
        print("Password: admin123")
        print("\n⚠️  IMPORTANT: Change the admin password in production!")
        
    except Exception as e:
        print(f"❌ Database setup failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()