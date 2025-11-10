# This file is part of HOMEctlx. Copyright (C) 2024 Christian Rauch.
# Distributed under terms of the GPL3 license.

"""
Authentication service for user login, session management, and access control.
"""

import logging
import bcrypt
from flask import session, request, redirect, render_template, make_response, current_app
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

import services.dbaccess as dba


log = logging.getLogger(__file__)


def get_serializer():
    """Get the token serializer using the app's secret key."""
    return URLSafeTimedSerializer(current_app.secret_key)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception as e:
        log.error(f"Password verification error: {e}")
        return False


def create_session(user: dict, remember: bool = False):
    """Create a session for the authenticated user."""
    session['uid'] = user['id']
    session['uname'] = user['name']
    session['upermissions'] = user['permissions']
    session.permanent = remember


def clear_session():
    """Clear the user session."""
    session.clear()


def get_current_user():
    """Get the currently logged in user information from session."""
    if 'uname' in session:
        return {
            'id': session.get('uid'),
            'uname': session.get('uname'),
            'upermissions': session.get('upermissions')
        }
    return None


def is_authenticated() -> bool:
    """Check if the current user is authenticated."""
    return 'uname' in session


def restore_session_from_cookie():
    """Try to restore session from remember_token cookie."""
    remember_token = request.cookies.get('remember_token')
    if remember_token:
        try:
            # Deserialize and verify the token
            serializer = get_serializer()
            uname = serializer.loads(remember_token, max_age=30*24*60*60)
            
            user = dba.get_user_by_name(uname)
            if user:
                create_session(user, remember=True)
                log.info(f"User '{user['name']}' session restored from signed cookie")
                return True
        except SignatureExpired:
            log.info("Remember token expired")
        except BadSignature:
            log.warning("Invalid remember token signature detected")
        except Exception as e:
            log.error(f"Error restoring session from cookie: {e}")
    return False


def set_remember_cookie(response, uname: str, max_age: int = 30*24*60*60):
    """Set the remember me cookie on a response with a signed token."""
    serializer = get_serializer()
    token = serializer.dumps(uname)
    
    response.set_cookie(
        'remember_token', 
        token, 
        max_age=max_age,
        httponly=True,
        secure=True,
        samesite='Strict'
    )
    return response


def clear_remember_cookie(response):
    """Clear the remember me cookie."""
    response.set_cookie('remember_token', '', expires=0)
    return response


def handle_login(uname: str, password: str, remember: bool = False):
    """
    Handle user login authentication.
    Returns (success: bool, response_or_error: str)
    """
    user = dba.get_user_by_name(uname)
    
    if user and verify_password(password, user['password_saltedhash']):
        # Successful login
        create_session(user, remember)
        dba.update_user_history(uname, 'Login')
        log.info(f"User '{uname}' logged in successfully")
        
        # Redirect to original destination or home
        next_page = request.args.get('next', '/')
        response = make_response(redirect(next_page))
        
        # Set remember me cookie if requested
        if remember:
            set_remember_cookie(response, user['name'])
        
        return True, response
    else:
        # Failed login
        log.warning(f"Failed login attempt for user '{uname}'")
        return False, 'Invalid username or password'


def handle_logout():
    """Handle user logout and return response."""
    uname = session.get('uname', 'unknown')
    clear_session()
    
    response = make_response(redirect('/login'))
    clear_remember_cookie(response)
    
    log.info(f"User '{uname}' logged out")
    return response


def require_authentication(public_routes=None):
    """
    Middleware to check if user is authenticated.
    Returns None if authenticated, redirect response if not.
    """
    if public_routes is None:
        public_routes = ['/login', '/static']
    
    # Check if the current route is public
    if any(request.path.startswith(route) for route in public_routes):
        return None
    
    # Check if user is authenticated
    if not is_authenticated():
        # Try to restore session from cookie
        if restore_session_from_cookie():
            return None
        
        # Not authenticated, redirect to login
        log.info(f"Unauthenticated access attempt to {request.path}")
        return redirect(f'/login?next={request.path}')
    
    return None


def render_login_page(error=None, message=None):
    """Render the login page with optional error or message."""
    # Check if already logged in
    if is_authenticated():
        return redirect('/')
    
    return render_template('login.html', error=error, message=message)
