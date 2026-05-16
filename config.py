import sys

from dotenv import load_dotenv
import os
import logging
from logging_loki import *
load_dotenv()

db_url = os.getenv("DATABASE_URL")
track_modify = True
table_prefix = os.getenv("DB_TABLE_PREFIX", "office")
api_key = os.getenv("API_KEY", "change_me")
master_secret = os.getenv("MASTER_SECRET", "change_me")
jwt_secret = os.getenv("JWT_SECRET", "change_me")
loki_url = os.getenv("LOKI_URL")
log_level = logging.DEBUG if os.getenv("DEBUG", "").lower() in ("true", "1") else logging.INFO

logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)
debug_mode = os.getenv("DEBUG")
if loki_url:
    loki_handler = LokiHandler(
        url=loki_url,
        tags={"application": "pulseid_backend"},
        version="1",
    )
    logger.addHandler(loki_handler)