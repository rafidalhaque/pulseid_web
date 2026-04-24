from dotenv import load_dotenv
import os
load_dotenv()

db_url = os.getenv("DATABASE_URL")
track_modify = True