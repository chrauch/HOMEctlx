#!/usr/bin/env python3
# This file is part of HOMEctlx. Copyright (C) 2024 Christian Rauch.
# Distributed under terms of the GPL3 license.

"""
User management script for HOMEctlx.
Create, delete, and manage users.
"""

import sys
import os
import bcrypt
import getpass

# Add parent directory to path to import services
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import services.dbaccess as dba


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def add_user(name: str, password: str, permissions: str = '', description: str = ''):
    """Add a new user to the database."""
    password_hash = hash_password(password)
    user_id = dba.add_user(name, password_hash, permissions, description)
    if user_id:
        print(f"✓ User '{name}' created successfully with ID {user_id}")
        return True
    else:
        print(f"✗ Failed to create user '{name}'. User may already exist.")
        return False


def delete_user(name: str):
    """Delete a user from the database."""
    user = dba.get_user_by_name(name)
    if user:
        dba.delete_user(name)
        print(f"✓ User '{name}' deleted successfully")
        return True
    else:
        print(f"✗ User '{name}' not found")
        return False


def list_users():
    """List all users."""
    users = dba.get_all_users()
    if not users:
        print("No users found in database")
        return
    
    print("\nUsers in database:")
    print("-" * 70)
    print(f"{'ID':<5} {'Name':<20} {'Permissions':<15} {'Description':<30}")
    print("-" * 70)
    for user in users:
        print(f"{user['id']:<5} {user['name']:<20} {user['permissions']:<15} {user['description']:<30}")
        print(f"{user['history']}")
    print("-" * 70)


def interactive_add_user():
    """Interactive mode to add a user."""
    print("\n=== Add New User ===")
    name = input("Username: ").strip()
    if not name:
        print("✗ Username cannot be empty")
        return
    
    password = getpass.getpass("Password: ")
    password2 = getpass.getpass("Confirm password: ")
    
    if password != password2:
        print("✗ Passwords do not match")
        return
    
    if len(password) < 4:
        print("✗ Password must be at least 4 characters")
        return
    
    permissions = input("Permissions: ").strip() or 'user'
    description = input("Description: ").strip()
    
    add_user(name, password, permissions, description)


def main():
    """Main function."""
    dba.init()
    
    if len(sys.argv) < 2:
        print("HOMEctlx User Management")
        print("\nUsage:")
        print("  python manage_users.py add                  - Add user interactively")
        print("  python manage_users.py add <name> <pass>    - Add user with name and password")
        print("  python manage_users.py delete <name>        - Delete user")
        print("  python manage_users.py list                 - List all users")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'add':
        if len(sys.argv) >= 4:
            name = sys.argv[2]
            password = sys.argv[3]
            permissions = sys.argv[4] if len(sys.argv) >= 5 else ''
            description = sys.argv[5] if len(sys.argv) >= 6 else ''
            add_user(name, password, permissions, description)
        else:
            interactive_add_user()
    
    elif command == 'delete':
        if len(sys.argv) < 3:
            print("✗ Please specify username to delete")
            sys.exit(1)
        delete_user(sys.argv[2])
    
    elif command == 'list':
        list_users()
    
    else:
        print(f"✗ Unknown command: {command}")
        sys.exit(1)
    
    dba.close_cached()


if __name__ == '__main__':
    main()
