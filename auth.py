import datetime
from functools import wraps
import jwt
from config import *
from flask import *

def generate_token(employee_id: str, employee_position: int):
    jwt_token = jwt.encode(
        {
            "sub": employee_id,
            "pos": str(employee_position),
            "iat": datetime.datetime.today(),
            "exp": datetime.datetime.today() + datetime.timedelta(minutes=30),
        },
        jwt_secret,
        algorithm="HS256",
    )
    return jwt_token

def check_secret_key(f):
    """
    secret api key for esp32
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        key = request.headers.get("Authorization")
        if not key:
            abort(401, "No API key provided")
        if key != api_key:
            abort(401, "Invalid API key")
        return f(*args, **kwargs)
    return decorated_function

def check_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            key = request.headers.get("Authorization")
            if not key:
                abort(401, "No API key provided")
            if not key.startswith("Bearer "):
                abort(401, "Invalid API key")
            the_key = key[7:]
            decoded_jwt = jwt.decode(the_key, jwt_secret, algorithms=["HS256"])
            g.employee_id = decoded_jwt["sub"]
            g.employee_position = decoded_jwt["pos"]
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            abort(401, "Signature expired")
        except jwt.InvalidTokenError:
            abort(401, "Invalid API key")
    return decorated_function