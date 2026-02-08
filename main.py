"""PeakStream Nervous System Scan API - Minimal Version"""
import os
from fastapi import FastAPI

app = FastAPI(title="PeakStream Scan API")

@app.get("/")
async def root():
    return {"status": "running", "service": "PeakStream Scan API"}

@app.get("/health")
async def health():
    return {"status": "healthy", "gemini_configured": bool(os.getenv("GEMINI_API_KEY"))}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
