from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import search
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router)


@app.get("/")
async def read_root():
    return {"message": "Welcome to the API"}
