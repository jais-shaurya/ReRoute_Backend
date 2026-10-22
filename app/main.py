import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.business import router as business_router
from app.api.planner import router as planner_router

app = FastAPI(
    title="ReRoute API",
    description="Intelligent Supply-Chain Disruption Planner",
    version="1.0.0",
)

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "REROUTE_CORS_ORIGINS",
        "http://localhost:5500,http://127.0.0.1:5500",
    ).split(",")
    if origin.strip()
]
if "*" in cors_origins:
    raise RuntimeError("REROUTE_CORS_ORIGINS must not contain a wildcard origin.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.get("/")
def root():
    return {
        "message": "ReRoute API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


app.include_router(auth_router)
app.include_router(planner_router)
app.include_router(business_router)
