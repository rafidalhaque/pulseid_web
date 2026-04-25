import pyotp, uuid
from config import *

def generate_secret_uuid():
    """
    employees.id + totp
    :return:
    """
    secret = pyotp.random_hex()
    gen_uuid = str(uuid.uuid4())
    return {
        "secret": secret}
