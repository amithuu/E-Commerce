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
    logo = business.logo
    logo_url = 'localhost:8000/static/images/'+logo
    
    return {
        'status':'ok',
        'data':
        {
         'username':user.username,
         'email':user.email,
         'verified':user.is_verified,
         'joined_date':user.join_date.strftime("%b %d %Y"),
         'profile_picture': logo_url
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


# this we are writing to upload file in business logo.. 
from fastapi import File, UploadFile
from PIL import Image
import secrets
from fastapi.staticfiles import StaticFiles

# set up for static files..
app.mount('/static', StaticFiles(directory='static'), name='static')


@app.post('/upload/picture')
async def upload_business_logo(file:UploadFile=File(...),
                               user:user_pydantic=Depends(get_current_user)): #type:ignore
    
    FILE_PATH = './static/images/'
    file_name = file.filename
    
    extension = file_name.split('.')[1]
    
    
    if extension not in ['jpg', 'png']:
        return {'error':'file format is wrong'}
    
    token_name = secrets.token_hex(5)+'.'+extension
    generated_name = FILE_PATH+token_name
    
    file_content = await file.read()
    
    with open(generated_name, 'wb') as file:
        file.write(file_content)

    img = Image.open(generated_name)
    img = img.resize(size=(200,200))
    img.save(generated_name)

    file.close()
           
    
    business = await Business.get(owner = user) 
    owner  = await business.owner
    
    if owner == user:
        business.logo = token_name
        await business.save()
        
        logo_url='localhost:8000'+generated_name[1:]
        return {
            'status':'ok',
            'logo':logo_url
        }
    else:
        raise HTTPException(
            detail='invalid user to upload file',
        )
    



@app.post('/upload.product_logo/{id}')
async def upload_product_logo(id:int, file:UploadFile=File(...),
                              user:user_pydantic=Depends(get_current_user)): # type:ignore
    
    FILE_PATH = './static/images/'
    file_name = file.filename
    
    extension = file_name.split('.')[1]
    
    
    if extension not in ['jpg', 'png']:
        return {'error':'file format is wrong'}
    
    token_name = secrets.token_hex(5)+'.'+extension
    generated_name = FILE_PATH+token_name
    
    file_content = await file.read()
    
    with open(generated_name, 'wb') as file:
        file.write(file_content)

    img = Image.open(generated_name)
    img = img.resize(size=(200,200))
    img.save(generated_name)

    file.close()
    
    product = await Product.get(id=id)
    business = await product.business
    owner = await business.owner
    
    if owner == user:
        product.product_image = token_name
        await product.save()
        
        product_url = 'localhost:8000'+generated_name[1:]
        return {
            'success': True,
            'image': product_url,
        }
        
    else:
        raise HTTPException(
            detail='invalid user to upload file',
        )
        
        
        
# Crud Functionality..[Create, Retrieve, Update, Delete]

#* Create Products..
@app.post('/products')
async def add_new__product(product:product_pydanticIn, user:user_pydantic=Depends(get_current_user)): # type:ignore
    
    product=product.dict(exclude_unset=True)
    
    if product['original_price']> 0:
        product['percentage_discount'] = ((product['original_price']-product['new_price']) / product['original_price'])*100

        product_obj =await Product.create(**product, business=user)
        product_create = await product_pydantic.from_tortoise_orm(product_obj)
        
        return {'status': 'created', 'Product': product_create}

    else:
        return {'status': 'error'}
    
#*Retrieve/List Products..
@app.get('/products/list')
async def list_products():
    data = await product_pydantic.from_queryset(Product.all())
    return {'success':'ok','products': data}




#Each item/product
@app.get('/products/{id}')
async def product_item(id:int):
    product = await Product.get(id=id)
    business = await product.business
    owner = await business.owner
    
    data = await product_pydantic.from_queryset_single(Product.get(id=id))
    
    return {
        'success':'ok',
        'data':{
            'products':data,
            'business_details':{
                'name':business.business_name,
                'city':business.city,
                'region':business.region,
                'business_description':business.business_description,
                'business_id':business.id,
                'logo':business.logo,
                'owner_id':owner.id,
                'owner_email':owner.email,
                'join_date':owner.join_date.strftime('%b %d %Y')
                                }
                }
            }



# Updating the data..
@app.put('/product/update/{id}')
async def update_product(id:int,product_info:product_pydanticIn , user:user_pydantic=Depends(get_current_user)): #type:ignore
    
    product = await Product.get(id=id)
    business = await product.business
    owner = await business.owner
    
    update_data = product_info.dict(exclude_unset=True)
    # update_data['date_published'] = datetime.utcnow()
    
    if user == owner and update_data['original_price'] > 0:
        update_data['percentage_discount'] = ((update_data['original_price'] - update_data['new_price']) / update_data['original_price']) *100
        
        product = await product.update_from_dict(update_data)
        await product.save()
        data =await product_pydantic.from_tortoise_orm(product)
        return {'success':'ok','data': data}
    
    else:
        return {'success':'error'}    


#Delete Product
@app.delete('/product/delete/{id}')
async def delete_product(id:int, user:user_pydantic=Depends(get_current_user)): # type: ignore
    
    product= await Product.get(id=id)
    business = await product.business
    owner = await business.owner
    
    if user == owner:
        product.delete()
    
    else:
        return{'success':'False'}
    
    return {'success':'Item Deleted successfully'}

     

#update business
@app.put('/business/update/{id}')
async def update_business(id:int, business_info:business_pydanticIn, user:user_pydantic=Depends(get_current_user)): # type: ignore
    
    business_data = business_info.dict()
    
    business =await Business.get(id=id)
    business_owner = await business.owner
        
    try:
        if user == business_owner:
            await business.update_from_dict(business_data)
            await business.save()
            
            response = await business_pydantic.from_tortoise_orm(business)
            
            return {'success':'Item Updated successfully', 'data':response}
    
    except Exception as e:
        return {'success':str(e)}
    
    
                
    
    
         
        
        
        
        
        
        
        
        
# settings       

register_tortoise(
    app,
    db_url = 'sqlite://database.sqlite3',
    modules={'models':['models']},
    generate_schemas=True,
    add_exception_handlers=True
)