from dotenv import load_dotenv
import os
load_dotenv()

db_url = os.getenv("DATABASE_URL")
track_modify = True
table_prefix = os.getenv("DB_TABLE_PREFIX", "office")
api_key = os.getenv("API_KEY", "change_me")
master_secret = os.getenv("MASTER_SECRET", "change_me")
jwt_secret = os.getenv("JWT_SECRET", "change_me")