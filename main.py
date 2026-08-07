import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


app = FastAPI(
    title="GFmotor API",
    description="GFmotor 改車系統的後端 API。",
    version="0.1.0",
)


frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        frontend_url,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount("/test", StaticFiles(directory="static"), name="static")


@app.get("/")
def read_root():
    return {"message": "歡迎來到 GFmotor API！"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


from api.router import api_router


app.include_router(api_router, prefix="/api")
