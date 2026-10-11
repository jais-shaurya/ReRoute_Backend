from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.business import router as business_router
from app.api.planner import router as planner_router
from app.database.connection import Base, SessionLocal, engine
from app.security.auth import ensure_bootstrap_user

app = FastAPI(
    title="ReRoute API",
    description="Intelligent Supply-Chain Disruption Planner",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.on_event("startup")
def bootstrap_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_bootstrap_user(db)
    finally:
        db.close()


app.include_router(planner_router)
app.include_router(business_router)
