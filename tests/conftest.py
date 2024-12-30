import pytest
import asyncio
import os
from pathlib import Path
from typing import Generator, AsyncGenerator

# Make sure we're using asyncio for pytest-asyncio
@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Temporary test directory
@pytest.fixture(scope="function")
def test_dir(tmp_path: Path) -> Path:
    return tmp_path

# Mock TPU environment
@pytest.fixture(scope="session")
def mock_tpu_environment() -> None:
    os.environ["TPU_LIBRARY_PATH"] = "/mock/path/lib"
    os.environ["TPU_CHIPS"] = "2"

# Mock model data
@pytest.fixture
def mock_model_data() -> bytes:
    return b"mock_model_data"

# Async client session
@pytest.fixture
async def async_client() -> AsyncGenerator:
    from aiohttp import ClientSession
    async with ClientSession() as session:
        yield session 