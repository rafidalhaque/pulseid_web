# tools.py
import hmac, hashlib
import uuid

from config import *

def gen_member_master_secret():
    secret = hmac.new(master_secret.encode(), (str(uuid.uuid4())).encode(), hashlib.sha256).hexdigest()
    return secret