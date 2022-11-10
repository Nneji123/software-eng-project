"""Endpoints defined by the dependency.
"""
import os
import re
from typing import List, Optional

import bcrypt
from dotenv import load_dotenv

load_dotenv()
from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from passwordgenerator import pwgenerator
from pydantic import BaseModel


from _auth._postgres_access import postgres_access
from _auth._security_secret import secret_based_security
from _auth._sqlite_access import sqlite_access

api_key_router = APIRouter()
templates = Jinja2Templates(directory='templates/')
api_key_router.mount('/templates/static', StaticFiles(directory="static"), name="static")


show_endpoints = "FASTAPI_AUTH_HIDE_DOCS" not in os.environ

try:
    DATABASE_MODE = os.getenv("DATABASE_MODE")
    if DATABASE_MODE == "postgres":
        dev = postgres_access
    else:
        dev = sqlite_access
except KeyError as e:
    print("DATABASE_MODE not set. Default=SQLite3 Database")
    dev = sqlite_access


def hash_password(password: str) -> str:
    """
    The hash_password function takes a string and returns the hashed version of that string.
    If no password is entered, it will return an error message.

    Args:
        password:str: Store the password that is entered by the user

    Returns:
        The hashed password
    """
    if password is not None:
        try:
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(str(password).encode("utf-8"), salt)
            return hashed.decode("utf-8")
        except Exception as e:
            print(e)
    else:
        return "Invalid Password entered"


def email_validate(email_text: str, request: Request):
    """
    The email_validate function takes in an email address as a string and returns the normalized form of that email address.
    If the inputted email is not valid, it raises an HTTPException with a status code of 403 Forbidden.

    Args:
        email_text:str: Store the email address that is inputted by the user

    Returns:
        The normalized form of the email address
    """
    try:
        if email_text != None:
            v = validate_email(email_text)
            # replace with normalized form
            email_text = v["email"]
            return email_text
        else:
            return templates.TemplateResponse("403_email.html", {"request": request})

    except (EmailNotValidError, AttributeError) as e:
        # email is not valid, exception message is human-readable
        return templates.TemplateResponse("403_email.html", {"request": request})



def check_length_password(password: str, request: Request) -> str:
    """
    The check_length_password function checks if the password is longer than 8 characters, contains an uppercase letter and digit.
    If it is not, then it will generate a new password for the user and return that instead.

    Args:
        password:str: Check if the password is at least 8 characters long, has a digit and an uppercase letter

    Returns:
        The password if it is longer than 8 characters, has at least one digit and uppercase letter
    """
    new_password = str(pwgenerator.generate())
    spec_char = re.compile("[@_!#$%^&*()<>?/\|}{~:]")
    if password == None or len(password) <= 8:
        return templates.TemplateResponse("403_password.html", {"request": request})

    elif re.search("[0-9]", password) is None:
        return templates.TemplateResponse("403_password.html", {"request": request})

    elif re.search("[A-Z]", password) is None:
        return templates.TemplateResponse("403_password.html", {"request": request})

    elif spec_char.search(password) == None:
        return templates.TemplateResponse("403_password.html", {"request": request})

    else:
        return password


@api_key_router.post(
    "/signin",
    dependencies=[Depends(secret_based_security)],
    include_in_schema=show_endpoints,
)
async def get_new_api_key(
    request: Request,
    username: str = Query(
        None,
        description="set API key username",
    ),
    email: str = Query(
        None,
        description="set API key email",
    ),
    password: str = Query(
        None,
        description="set API key password. Must contain at least one uppercase letter, a digit and a special character.",
    ),
    never_expires: bool = Query(
        False,
        description="if set, the created API key will never be considered expired",
    ),
 
) -> str:
    """
    Returns:
        api_key: a newly generated API key
    """
    if request.method == "POST":
        form = await request.form()
        if (form["email"] and form["username"] and form["password"]):
            password = form["password"]
            username = form["username"]
            email = form["email"]
            if password != "":
                password = check_length_password(password)
                password = hash_password(password)
            else:
                return templates.TemplateResponse("index.html", {"request": request})

            if email != "":
                email = email_validate(email)
        else:
            return templates.TemplateResponse("upload.html", {"request": request, "email": email, "password": password, "username": username})

    
    return dev.create_key(username, email, password, never_expires), templates.TemplateResponse("upload.html", {"request": request})


# Admin endpoints
@api_key_router.get(
    "/revoke",
    dependencies=[Depends(secret_based_security)],
    include_in_schema=show_endpoints,
)
def revoke_api_key(
    api_key: str = Query(..., alias="api-key", description="the api_key to revoke")
):
    """
    Revokes the usage of the given API key

    """
    return dev.revoke_key(api_key)


@api_key_router.get(
    "/renew",
    dependencies=[Depends(secret_based_security)],
    include_in_schema=show_endpoints,
)
def renew_api_key(
    api_key: str = Query(..., alias="api-key", description="the API key to renew"),
    expiration_date: str = Query(
        None,
        alias="expiration-date",
        description="the new expiration date in ISO format",
    ),
):
    """
    Renews the chosen API key, reactivating it if it was revoked.
    """
    return dev.renew_key(api_key, expiration_date)


class UsageLog(BaseModel):
    api_key: str
    username: Optional[str]
    is_active: bool
    never_expire: bool
    expiration_date: str
    latest_query_date: Optional[str]
    total_queries: int
    email: str


class UsageLogs(BaseModel):
    logs: List[UsageLog]


@api_key_router.get(
    "/logs",
    dependencies=[Depends(secret_based_security)],
    response_model=UsageLogs,
    include_in_schema=show_endpoints,
)
def get_api_key_usage_logs():
    """
    Returns usage information for all API keys
    """
    # TODO Add some sort of filtering on older keys/unused keys?

    return UsageLogs(
        logs=[
            UsageLog(
                api_key=row[0],
                is_active=row[1],
                never_expire=row[2],
                expiration_date=row[3],
                latest_query_date=row[4],
                total_queries=row[5],
                username=row[6],
                email=row[7],
            )
            for row in dev.get_usage_stats()
        ]
    )
