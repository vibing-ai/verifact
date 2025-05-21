from fastapi import FastAPI
from api.factcheck import router as factcheck_router

app = FastAPI(
    title="Fact Check API",
    description="API for fact-checking claims in text",
    version="1.0.0"
)

app.include_router(factcheck_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
