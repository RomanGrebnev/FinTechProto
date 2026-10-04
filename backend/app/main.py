import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, engine
from .routers import advice, auth, portfolio, profile

logging.basicConfig(level=logging.INFO)

Base.metadata.create_all(engine)

app = FastAPI(title="Wealthpilot API", version="0.1.0")
# The frontend is served behind the same origin in Docker; this allows `npm run dev` on :5173
app.add_middleware(
    CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"],
)

for r in (auth.router, profile.router, portfolio.router, advice.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    return {"status": "ok"}
