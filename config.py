import sys

from dotenv import load_dotenv
import os
import logging
from logging_loki import *
from cloudflare import Cloudflare


load_dotenv()

class SafeLokiHandler(logging.Handler):
    """A wrapper around LokiHandler that silently handles Loki failures."""
    
    def __init__(self, loki_handler):
        super().__init__()
        self.loki_handler = loki_handler
    
    def emit(self, record):
        try:
            self.loki_handler.emit(record)
        except Exception as e:
            # Silently ignore Loki failures to prevent cascading errors
            # The error is already logged by the underlying handler
            pass

db_url = os.getenv("DATABASE_URL")
track_modify = True
table_prefix = os.getenv("DB_TABLE_PREFIX", "office")
api_key = os.getenv("API_KEY", "change_me")
master_secret = os.getenv("MASTER_SECRET", "change_me")
jwt_secret = os.getenv("JWT_SECRET", "change_me")
loki_url = os.getenv("LOKI_URL")
log_level = logging.DEBUG if os.getenv("DEBUG", "").lower() in ("true", "1") else logging.INFO
cf_client = Cloudflare(
    api_key=os.getenv("CF_API_TOKEN"),
)
cf_bucket_name = os.getenv("CF_BUCKET_NAME")
cf_ac_id = os.getenv("CF_ACCOUNT_ID")
cf_public = os.getenv("CF_PUBLIC_URL")
release_key = os.getenv("RELEASE_KEY")
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)
metrics_logger = logging.getLogger("pulseid.metrics")
debug_mode = os.getenv("DEBUG")
if loki_url:
    loki_handler = LokiHandler(
        url=loki_url,
        tags={"application": "pulseid_backend"},
        version="1",
    )
    safe_loki_handler = SafeLokiHandler(loki_handler)
    logger.addHandler(safe_loki_handler)
    
    metrics_loki = LokiHandler(
        url=loki_url,
        tags={"application": "pulseid_backend", "type": "esp32_metrics"},
        version="1",
    )
    safe_metrics_loki = SafeLokiHandler(metrics_loki)
    metrics_logger.addHandler(safe_metrics_loki)
