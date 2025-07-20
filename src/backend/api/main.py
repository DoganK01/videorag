# src/app/api/main.py
import logging.config
from contextlib import asynccontextmanager

import yaml
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from app.api.dependencies import AppState, init_dependencies, close_dependencies
from app.api.routers import query_router, indexing_router, library_router
from app.core.schemas import TaskError


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events. This is the central point for
    initializing and cleaning up all application resources.
    """
    load_dotenv()
    
    try:
        with open("configs/logging_config.yaml", "rt") as f:
            log_config = yaml.safe_load(f.read())
        logging.config.dictConfig(log_config)
    except FileNotFoundError:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s')
    
    logger = logging.getLogger(__name__)
    logger.info("--- Application Starting Up ---")

    try:
        with open("configs/main_config.yaml", "rt") as f:
            app_config = yaml.safe_load(f.read())
    except FileNotFoundError:
        logger.critical("main_config.yaml not found. Application cannot start.")
        raise
    
    app_state = await init_dependencies(app_config)
    app.state.app_state = app_state
    
    yield
    
    logger.info("--- Application Shutting Down ---")
    await close_dependencies(app.state.app_state)



app = FastAPI(
    title="VideoRAG API",
    description="API for Retrieval-Augmented Generation with Extreme Long-Context Videos",
    version="1.0.0",
    lifespan=lifespan
)

@app.exception_handler(TaskError)
async def task_error_exception_handler(request: Request, exc: TaskError):
    logging.getLogger(__name__).error(f"A handled task error occurred: {exc.message}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": f"An internal error occurred in task '{exc.task_name}': {exc.message}"},
    )

API_PREFIX = "/api/v1"
app.include_router(query_router, prefix=API_PREFIX, tags=["Query"])
app.include_router(indexing_router, prefix=API_PREFIX, tags=["Indexing"])
app.include_router(library_router, prefix=API_PREFIX, tags=["Library"])

@app.get("/", tags=["Health"])
async def read_root():
    """A simple health check endpoint to verify that the API service is running."""
    return {"status": "ok", "message": "Welcome to the VideoRAG API"}