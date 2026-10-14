import sys
sys.path.insert(0, '.')

from app.core.config import Settings

settings = Settings()
print("DATABASE_URL:", settings.database_url)
