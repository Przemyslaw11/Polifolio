from fastapi_app.services.stock_service import scheduler
from shared.logging_config import setup_logging
from fastapi_app.db.database import init_db
from fastapi_app.api.routes import router
from fastapi import FastAPI
from typing import Dict

logger = setup_logging()
app = FastAPI()

app.include_router(router)


@app.on_event("startup")
async def startup_event() -> None:
    """
    Initialize the database and start the scheduler on application startup.
    args: None
    return: None
    """
    logger.info("Starting up FastAPI application")
    init_db()
    if not scheduler.running:
        scheduler.start()
    logger.info("Scheduler started")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Shut down the scheduler on application shutdown.
    args: None
    return: None
    """
    if scheduler.running:
        scheduler.shutdown()
    logger.info("Scheduler shut down")


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
    """
    Get the current status of the scheduler.
    args: None
    return: A dictionary containing the scheduler's running status and job count
    """


async def scheduler_status():
    return {"is_running": scheduler.running, "job_count": len(scheduler.get_jobs())}
