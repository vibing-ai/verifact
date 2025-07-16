from dotenv import load_dotenv
from fastapi import FastAPI

from api.factcheck import router as factcheck_router
from utils.logging_utils.logging_config import setup_logging

load_dotenv()
setup_logging()

app = FastAPI(
    title="Fact Check API",
    description="API for fact-checking claims in text",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {"message": "Welcome to VeriFact Fast API!"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

app.include_router(factcheck_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)