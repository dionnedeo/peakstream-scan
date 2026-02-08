
@app.post("/api/scan/test")
async def test_scan():
    if not GEMINI_API_KEY:
        raise HTTPException(500, "Gemini not configured")
    test = {"business_name": "Denver Plumbing Pro", "website_url": "https://example.com",
            "industry": "Plumbing", "city": "Denver", "state": "CO", "google_rating": 4.6, "review_count": 47}
    try:
        results = run_scan(test)
        return {"success": True, "test_business": test, "scan_results": results}
    except Exception as e:
        raise HTTPException(500, str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
