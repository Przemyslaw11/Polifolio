from .routes import router
from fastapi import FastAPI
from sqlalchemy.orm import Session
from shared.database import init_db

app = FastAPI()

app.include_router(router)


@app.on_event("startup")
async def startup_event():
    init_db()


@app.get("/")
async def root():
    return {"message": "Welcome to the Polifolio supported by FastAPI!"}
