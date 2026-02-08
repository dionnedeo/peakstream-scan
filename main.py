"""PeakStream Scan API"""
import os, json
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
Output JSON with: overall_score, category (Invisible/Weak/Moderate/Strong/Dominant), summary, modules (array with name/score/max_score/strength/observations), key_findings (3 items), recommendations (3 items with action/impact_points/reasoning/expected_outcome)"""

SOCIAL_PROMPT = """Generate 3 social posts for {business_name} ({industry}, {city}). Score: {scan_score}/100.
Output JSON array: [{{"topic": "...", "text": "...", "best_for": "...", "when_to_post": "..."}}]"""

def run_scan(d):
    model = genai.GenerativeModel("gemini-2.5-flash", generation_config={"temperature": 0.7, "response_mime_type": "application/json"})
    return json.loads(model.generate_content(SCAN_PROMPT.format(**d)).text)

def run_social(name, ind, city, score):
    model = genai.GenerativeModel("gemini-2.5-flash", generation_config={"temperature": 0.8, "response_mime_type": "application/json"})
    return json.loads(model.generate_content(SOCIAL_PROMPT.format(business_name=name, industry=ind, city=city, scan_score=score)).text)

def format_email(name, r, posts):
    s = r["overall_score"]
    h = f"<h2>SCAN REPORT: {name}</h2><p>Score: {s}/100 ({r['category']})</p><p>{r['summary']}</p>"
    for m in r.get("modules", []): h += f"<p><b>{m['name']}: {m['score']}/{m['max_score']}</b></p>"
    h += "<h3>Findings</h3><ul>"
    for f in r.get("key_findings", []): h += f"<li>{f}</li>"
    h += "</ul><h3>Recommendations</h3><ul>"
    for x in r.get("recommendations", []): h += f"<li>{x['action']}</li>"
    h += "</ul><p>Best, DD - PeakStream House</p>"
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
        p = run_social(req.business_name, req.industry, req.city, r["overall_score"])
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
