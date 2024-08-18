from functools import wraps
from flask_jwt_extended import get_jwt_identity
from flask import abort
from .models import *
import uuid
import os

# Decorator for authenticating the user
def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            current_user = get_jwt_identity()
            if current_user['role'] != required_role:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator

def generate_unique_name_for_file(file):
    if not file:
        return None
    
    # Generate Unique ID for the file
    unique_id = str(uuid.uuid4())
    path = f"{unique_id}_{file.filename}"

    return path

def create_image_path(file_name, file_type):
    # Normalize the path to resolve '..'
    path = r'{}/{}'.format(file_type, file_name)

    return path
