from sqlalchemy.ext.asyncio import create_async_engine
from app.config.settings import settings

# Create Async Engine
# We use echo=True only in debug mode to see queries in logs
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,
    future=True,
)
