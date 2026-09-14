from contextlib import asynccontextmanager
import logging
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI
from fastapi.responses import JSONResponse
from seriousdb.logging_config import configure_logging

from .cache import Cache
from .config import DB_FILE

cache = Cache()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    cache.load(DB_FILE)
    yield


app = FastAPI(lifespan=lifespan)


def get_cache() -> Cache:
    return cache


@app.put("/db")
def put(
    key: str,
    value: str,
    background_tasks: BackgroundTasks,
    cache: Annotated[Cache, Depends(get_cache)],
):
    cache.insert(key, value)
    background_tasks.add_task(cache.flush)
    return value


@app.get("/db")
def get(key: str, cache: Annotated[Cache, Depends(get_cache)]):
    return cache.select(key)


@app.delete("/db")
def delete(key: str, cache: Annotated[Cache, Depends(get_cache)]):
    return cache.delete(key)


@app.exception_handler(Exception)
async def global_handle_exception(request, exc):
    logger.exception("Unexpected application error: %s", exc)
    return JSONResponse(status_code=500, content={"message": "Internal Server Error."})
