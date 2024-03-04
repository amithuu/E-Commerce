from fastapi import FastAPI, Request, Depends
from models import *
from tortoise.contrib.fastapi import register_tortoise

app=FastAPI()

# so when the user created the account from our end we are creating their business account as well..
from tortoise.signals import post_save
from typing import List, Optional, Type
from tortoise import BaseDBAsyncClient
from emails import *
from fastapi.responses import HTMLResponse
from authentication import *
from fastapi.templating import Jinja2Templates
from fastapi import HTTPException, status

templates= Jinja2Templates(directory='templates')

@app.get('/verification', response_class=HTMLResponse)
async def email_verification(request:Request, token:str):
    user = await verify_token(token)
    
    if user and not user.is_verified:
        user.is_verified=True
        await user.save()
        return templates.TemplateResponse('verification.html',
                                          {'request':request, 'username':user.username})
    
    raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='user not authorized, or invalid token or expired'
        )


@post_save(User)
async def create_business_account(
    sender:'Type[User]',
    instance :User,
    created:bool,
    using_db : 'Optional[BaseDBAsyncClient]',
    update_fields : List[str]
) -> None:
    
    if created:
        business_obj = await Business.create(business_name=instance.username, owner=instance)
        await business_pydantic.from_tortoise_orm(business_obj)
        # send email next part..
        await send_email([instance.email], instance)

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm #[need to install python-multipart] for form to run..


@app.post('/token')
async def generate_token(form:OAuth2PasswordRequestForm=Depends()):
    token = await token_generator(form.username, form.password)
    return {'access_token':token, "token_type":'bearer'}


oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')
 
async def get_current_user(token:str=Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, config_credentials['SECRET'], algorithms=['HS256'])
        user = await User.get(id = payload.get('id'))
        return user
    
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='invalid username',
        )  

@app.post('/user/me')
async def user_login(user:user_pydanticIn=Depends(get_current_user)): # type:ignore
    business = await Business.get(owner = user)
    
    return {
        'status':'ok',
        'data':
        {
         'username':user.username,
         'email':user.email,
         'verified':user.is_verified,
         'joined_date':user.join_date.strftime("%b %d %Y")   
        }
    }


# do user registration with user details..
from authentication import get_hashed_password
@app.post('/register')
async def register_user(user:user_pydanticIn): # type:ignore
    user_info= user.dict(exclude_unset=True)
    user_info['password'] =  get_hashed_password(user_info['password'])
    user_obj = await User.create(**user_info)
    new_user = await user_pydantic.from_tortoise_orm(user_obj)
    return {
        'status':'ok',
        'data':f'hello {new_user.username},thanks for creating account in our site, please check your email to verify by clicking on the link provided..'
    }   



register_tortoise(
    app,
    db_url = 'sqlite://database.sqlite3',
    modules={'models':['models']},
    generate_schemas=True,
    add_exception_handlers=True
)
