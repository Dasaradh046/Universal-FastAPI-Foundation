import os
from dotenv import load_dotenv

load_dotenv()  # Take environment variables from .env.

print("DB_HOST:", os.getenv("DB_HOST"))
print("SECRET_KEY:", os.getenv("SECRET_KEY"))
