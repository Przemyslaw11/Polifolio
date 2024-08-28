from shared.logging_config import setup_logging
from shared.database import init_db
from .tasks import scheduler
from fastapi import FastAPI
from .routes import router

logger = setup_logging()

app = FastAPI()

app.include_router(router)



@app.on_event("startup")
async def startup_event():
    logger.info("Starting up FastAPI application")
    init_db()

    if not scheduler.running:
        scheduler.start()


@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to the Polifolio supported by FastAPI!"}


@app.get("/scheduler-status")
async def scheduler_status():
    return {"is_running": scheduler.running, "job_count": len(scheduler.get_jobs())}
