#!/usr/bin/env python3
"""
Development environment setup script
Creates a minimal .env file for testing the authentication system
"""

import os
import secrets

def generate_secret_key():
    """Generate a random secret key for JWT"""
    return secrets.token_urlsafe(32)

def create_dev_env():
    """Create a development .env file"""
    env_path = os.path.join('app', '.env')
    
    if os.path.exists(env_path):
        response = input(f".env file already exists at {env_path}. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled. Using existing .env file.")
            return
    
    # Get database credentials
    print("Setting up development environment...")
    print("Please provide your database credentials:")
    
    db_user = input("Database user (default: root): ").strip() or "root"
    db_pass = input("Database password: ").strip()
    db_host = input("Database host (default: localhost): ").strip() or "localhost"
    db_name = input("Database name (default: agy_intelligence_hub): ").strip() or "agy_intelligence_hub"
    
    # Generate random tokens for development
    secret_key = generate_secret_key()
    dummy_token = secrets.token_urlsafe(16)
    webhook_token = secrets.token_urlsafe(16)
    
    env_content = f"""# AGY Intelligence Hub - Development Environment
# Generated automatically for development/testing

# Authentication & Security
SECRET_KEY={secret_key}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Database Configuration
DB_USER={db_user}
DB_PASS={db_pass}
DB_HOST={db_host}
DB_NAME={db_name}
INSTANCE_UNIX_SOCKET=

# Development/Testing Tokens (randomly generated)
DITAT_TOKEN=dev_ditat_token_123
SAMSARA_TOKEN=dev_samsara_token_123
DUMMY_TOKEN={dummy_token}
WEBHOOK_TOKEN={webhook_token}

# Slack Integration (Development placeholders)
SLACK_BOT_TOKEN=xoxb-dev-token-placeholder
SLACK_SIGNING_SECRET=dev_signing_secret_placeholder
ALERTS_APPROACH1_SLACK_CHANNEL=#ai-temp-testing
ALERTS_APPROACH2_SLACK_CHANNEL=#ai-temp-alerts

# Optional Services (Leave empty for development)
VAPI_API_KEY=
VAPI_ASSISTANT_ID=
VAPI_PHONENUMBER_ID=
PCMILER_API_KEY=

# Application Settings
PORT=8000
CLOUD_RUN_URL=http://localhost:8000
"""
    
    try:
        with open(env_path, 'w') as f:
            f.write(env_content)
        
        print(f"\n✅ Development .env file created at: {env_path}")
        print("\n🔐 Generated secure tokens:")
        print(f"   SECRET_KEY: {secret_key}")
        print(f"   DUMMY_TOKEN: {dummy_token}")
        print(f"   WEBHOOK_TOKEN: {webhook_token}")
        
        print(f"\n📋 Database configuration:")
        print(f"   Host: {db_host}")
        print(f"   Database: {db_name}")
        print(f"   User: {db_user}")
        
        print(f"\n🚀 Next steps:")
        print(f"   1. Make sure your MySQL database '{db_name}' exists")
        print(f"   2. Run: python app/setup_database.py")
        print(f"   3. Run: python app/main.py")
        
    except Exception as e:
        print(f"❌ Error creating .env file: {e}")

if __name__ == "__main__":
    create_dev_env()