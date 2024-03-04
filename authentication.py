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



async def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


async def authenticate_user(username, password):
    user = await User.get(username=username)
    if user and verify_password(password, user.password):
        return user
    return False


async def token_generator(username:str, password:str):
    user = await authenticate_user(username, password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='invalid username',
        )
    
    token_data = {
        'id':user.id,
        'username':user.username       
    }
    
    token = jwt.encode(token_data, config_credentials['SECRET'], algorithm='HS256')
    
    return token