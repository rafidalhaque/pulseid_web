import datetime
from functools import wraps
import jwt
from config import *
from flask import *

def generate_token(employee_id: str, employee_position: int, employee_is_admin: bool):
    dt_t = datetime.datetime.now(datetime.timezone.utc)
    logger.debug(f"datetime today {dt_t}")
    jwt_token = jwt.encode(
        {
            "sub": str(employee_id),
            "pos": str(employee_position),
            "adm": employee_is_admin,
            "iat": dt_t,
            "exp": dt_t + datetime.timedelta(minutes=720),
        },
        jwt_secret,
        algorithm="HS256",
    )
    logger.debug(f"jwt token {jwt_token} for employee {employee_id}")
    return jwt_token

def check_secret_key(f):
    """
    secret api key for esp32
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        key = request.headers.get("X-Admin-Key")
        if not key:
            logger.warn("X-Admin-Key not provided")
            abort(401, "No API key provided")
        if key != api_key:
            logger.warn("X-Admin-Key not provided")
            abort(401, "Invalid API key")
        return f(*args, **kwargs)
    return decorated_function

def check_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            key = request.headers.get("Authorization")
            if not key:
                logger.warn("Authorization header is not provided")
                abort(401, "No API key provided")
            if not key.startswith("Bearer "):
                logger.warn("Authorization header does not start with Bearer")
                abort(401, "Invalid API key")
            the_key = key[7:]
            logger.debug(f"token received: [{the_key}]")
            decoded_jwt = jwt.decode(the_key, jwt_secret, algorithms=["HS256"])
            g.employee_id = decoded_jwt["sub"]
            g.employee_position = decoded_jwt["pos"]
            g.is_admin = decoded_jwt["adm"]
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            logger.warn("Signature expired")
            abort(401, "Signature expired")
        except jwt.InvalidTokenError:
            logger.warn("Invalid token")
            abort(401, "Invalid API key")
        except Exception as e:
            logger.warn(f"Unknown error: {e}")
    return decorated_function