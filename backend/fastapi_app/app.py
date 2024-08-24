from shared.database import init_db
from fastapi import FastAPI
from .routes import router

app = FastAPI()

app.include_router(router)


@app.on_event("startup")
async def startup_event():
    init_db()


@app.get("/")
async def root():
    return {"message": "Welcome to the Polifolio supported by FastAPI!"}
