from fastapi import FastAPI
from models import *
from tortoise.contrib.fastapi import register_tortoise

app=FastAPI()

# so when the user created the account from our end we are creating their business account as well..
from tortoise.signals import post_save
from typing import List, Optional, Type
from tortoise import BaseDBAsyncClient

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
