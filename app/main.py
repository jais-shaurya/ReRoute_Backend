from fastapi import FastAPI

from app.api.planner import router as planner_router


app = FastAPI(
    title="ReRoute API",
    description="Intelligent Supply-Chain Disruption Planner",
    version="1.0.0",
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


app.include_router(planner_router)
