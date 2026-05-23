from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="ETH/USDT Signal API", version="1.0.0")

class HealthCheck(BaseModel):
    status: str

@app.get("/health", response_model=HealthCheck)
async def health_check():
    return {"status": "ok", "message": "API is running"}
