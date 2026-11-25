from fastapi import FastAPI

app = FastAPI(
    title="AI Quality Engineering Platform",
    description="AI-powered Quality Engineering and Test Automation Platform",
    version="1.0.0"
)


@app.get("/")
def root():
    return {
        "message": "Welcome to AI Quality Engineering Platform",
        "status": "running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "application": "AI Quality Engineering Platform",
        "version": "1.0.0"
    }