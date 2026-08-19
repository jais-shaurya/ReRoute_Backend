from fastapi import FastAPI

app = FastAPI(
    title="ReRoute API",
    description="Intelligent Supply-Chain Disruption Planner",
    version="1.0.0"
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