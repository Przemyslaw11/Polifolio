from fastapi_app.routes import router
from fastapi import FastAPI

app = FastAPI()

app.include_router(router)

@app.get("/")
async def root():
    return {"message": "Welcome to the Polifolio supported by FastAPI!"}
