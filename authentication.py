from passlib.context import CryptContext

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def get_hashed_password(password):
    return pwd_context.hash(password)



import jwt
from dotenv import dotenv_values
from models import *
from fastapi import HTTPException, status


config_credentials =dotenv_values('.env')
async def verify_token(token:str):
    try:
        payload = jwt.decode(token, config_credentials['SECRET'], algorithms=['HS256'])
        user = await User.get(id = payload.get('id'))
        
    
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='user not authorized, or invalid token'
        )
    
    return user