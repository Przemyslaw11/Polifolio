from typing import Dict

from fastapi import FastAPI

from fastapi_app.services.scheduler_service import start_scheduler
from fastapi_app.services.stock_service import scheduler
from fastapi_app.db.database import init_db
from fastapi_app.api.routes import router
from shared.config import logger

app = FastAPI()
app.include_router(router)


@app.on_event("startup")
async def startup_event():
    logger.info("Starting up FastAPI application")
    await init_db()
    if not scheduler.running:
        start_scheduler()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Shut down the scheduler on application shutdown.
    args: None
    return: None
    """
    if scheduler.running:
        scheduler.shutdown()


@app.get("/")
async def root() -> Dict[str, str]:
    """
    Serve the root endpoint of the application.
    args: None
    return: A dictionary containing a welcome message
    """
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to Polifolio supported by FastAPI!"}


async def scheduler_status() -> Dict[str, bool | int]:
    return {"is_running": scheduler.running, "job_count": len(scheduler.get_jobs())}
