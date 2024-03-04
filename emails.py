from fastapi_mail import ConnectionConfig, MessageSchema, MessageType, FastMail
from typing import List
from dotenv import dotenv_values
from models import *
import jwt

config_credentials = dotenv_values('.env')

config = ConnectionConfig(
    MAIL_USERNAME=config_credentials['EMAIL'],
    MAIL_PASSWORD=config_credentials['PASS'],
    MAIL_FROM=config_credentials['EMAIL'],
    MAIL_PORT=465,
    MAIL_SERVER='smtp.gmail.com',
    MAIL_SSL_TLS=True,
    MAIL_STARTTLS = False,
    USE_CREDENTIALS=True,
    TEMPLATE_FOLDER= './templates'
)



async def send_email(email: List, instance: User):
    
    # creating a token 
    token_data={
        'id':instance.id,
        'username':instance.username,
    }
    
    token = jwt.encode(token_data, config_credentials['SECRET'], algorithm='HS256')
    
    template =f""" 
    <!DOCTYPE html>
    <html>
        <head>
    
        </head>
        <body>
            <div style='display:flex;align-items:center;justify-content:center;flex-direction:column'>
                <h3> Account Verification</h3>
                <br>
                
                <p> Thanks for verifying here </p>
                
                <a style="margin-top:1rem; padding:1rem; border-radius:0.5rem;
                font-size:1rem; text-decoration:none; background: #0275d8; color:white;"
                href="http://localhost:8000/verification/?token={token}">
                Verify Email
                </a>
                
        </body>
    </html>"""
    
    
    message = MessageSchema(
        subject='email_verification',
        recipients=email,
        body=template,
        subtype=MessageType.html,
    )

    fm = FastMail(config)
    await fm.send_message(message=message)
    pass
