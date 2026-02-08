"""PeakStream Scan API"""
import os, json, re
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai

app = FastAPI(title="PeakStream Scan API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY: genai.configure(api_key=GEMINI_API_KEY)
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "peakstream-secret-2024")

class ScanRequest(BaseModel):
    business_name: str
    website_url: Optional[str] = None
    industry: str
    city: str
    state: str = "CO"
    google_rating: Optional[float] = None
    review_count: Optional[int] = 0

class ScanResponse(BaseModel):
    success: bool
    scan_results: Dict[str, Any]
    social_posts: List[Dict[str, str]]
    email_body: str

SCAN_PROMPT = """Analyze this business for AI visibility. Score 0-100.
Business: {business_name} | {website_url} | {industry} | {city}, {state}
Rating: {google_rating}/5 | Reviews: {review_count}
Respond with ONLY valid JSON (no markdown): {{"overall_score": N, "category": "...", "summary": "...", "modules": [...], "key_findings": [...], "recommendations": [...]}}"""

SOCIAL_PROMPT = """Generate 3 social posts for {business_name} ({industry}, {city}). Score: {scan_score}/100.
Respond with ONLY valid JSON array (no markdown): [{{"topic": "...", "text": "...", "best_for": "...", "when_to_post": "..."}}]"""

def extract_json(text):
    text = re.sub(r'^```json\s*', '', text.strip())
    text = re.sub(r'\s*```$', '', text)
    return json.loads(text)

def run_scan(d):
    model = genai.GenerativeModel("gemini-2.5-flash")
    resp = model.generate_content(SCAN_PROMPT.format(**d))
    return extract_json(resp.text)

def run_social(name, ind, city, score):
    model = genai.GenerativeModel("gemini-2.5-flash")
    resp = model.generate_content(SOCIAL_PROMPT.format(business_name=name, industry=ind, city=city, scan_score=score))
    return extract_json(resp.text)

def format_email(name, r, posts):
    s = r.get("overall_score", 0)
    h = f"<h2>SCAN: {name}</h2><p>Score: {s}/100 ({r.get('category', 'N/A')})</p><p>{r.get('summary', '')}</p>"
    return h

@app.get("/")
async def root(): return {"service": "PeakStream Scan API", "status": "running"}

@app.get("/health")
async def health(): return {"status": "healthy", "gemini_configured": bool(GEMINI_API_KEY)}

@app.post("/api/scan", response_model=ScanResponse)
async def scan(req: ScanRequest, authorization: str = Header(None)):
    if authorization != f"Bearer {WEBHOOK_SECRET}": raise HTTPException(401, "Unauthorized")
    if not GEMINI_API_KEY: raise HTTPException(500, "Gemini not configured")
    try:
        d = {"business_name": req.business_name, "website_url": req.website_url or "N/A", "industry": req.industry, "city": req.city, "state": req.state, "google_rating": req.google_rating or "N/A", "review_count": req.review_count or 0}
        r = run_scan(d)
        p = run_social(req.business_name, req.industry, req.city, r.get("overall_score", 50))
        return ScanResponse(success=True, scan_results=r, social_posts=p, email_body=format_email(req.business_name, r, p))
    except Exception as e: raise HTTPException(500, str(e))

@app.post("/api/scan/test")
async def test():
    if not GEMINI_API_KEY: raise HTTPException(500, "Gemini not configured")
    d = {"business_name": "Test Plumber", "website_url": "example.com", "industry": "Plumbing", "city": "Denver", "state": "CO", "google_rating": 4.5, "review_count": 50}
    try: return {"success": True, "scan_results": run_scan(d)}
    except Exception as e: raise HTTPException(500, str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
