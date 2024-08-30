from fastapi_app.services.stock_service import scheduler
from shared.logging_config import setup_logging
from fastapi_app.db.database import init_db
from fastapi_app.api.routes import router
from fastapi import FastAPI

logger = setup_logging()
app = FastAPI()

app.include_router(router)


@app.on_event("startup")
async def startup_event():
    logger.info("Starting up FastAPI application")
    init_db()
    if not scheduler.running:
        scheduler.start()
    logger.info("Scheduler started")


@app.on_event("shutdown")
async def shutdown_event():
    if scheduler.running:
        scheduler.shutdown()
    logger.info("Scheduler shut down")


@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to Polifolio supported by FastAPI!"}


@app.get("/scheduler-status")
async def scheduler_status():
    return {"is_running": scheduler.running, "job_count": len(scheduler.get_jobs())}
