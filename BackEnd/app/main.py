# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db
from .routers import ui_router, edge_router

app = FastAPI(title="Watering System Server (Edge + Local)")

# CORS: biar FE bisa akses dari localhost / IP lain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # bisa dipersempit nanti
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()
    print("[SERVER] DB ready.")

# include routers
app.include_router(ui_router.router)
app.include_router(edge_router.router)
