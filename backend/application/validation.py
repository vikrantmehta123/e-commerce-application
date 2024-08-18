from application.models import *

def validate_role(user:User, role:str):
    if role not in [role.name for role in user.roles]:
        raise Exception
    
    