import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from src.app.core.config import settings
from src.app.core.database import get_db
from src.app.main import app

@pytest.fixture
def anyio_backend():
    return "asyncio"

test_engine = create_async_engine(settings.DB_URL, echo=False, poolclass=NullPool)

# Dibuat di modul ini (bukan di dalam fixture) supaya tes bisa membutuhkannya
# untuk membersihkan sisa data yang dibuat tes lain.
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with TestSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db
