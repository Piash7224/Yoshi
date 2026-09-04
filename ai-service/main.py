from fastapi import FastAPI
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Yoshi AI Service Engine")

@app.get("/health")
def health_check():
    return {
        "status": "OK",
        "message": "AI service engine skeleton is running flawlessly."
    }
