from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from app import models
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+psycopg2://postgres:postgres@db:5432/jpm_intel')

app = FastAPI()
app.mount("/static", StaticFiles(directory="./static"), name="static")

# simple logger attribute
import logging
app.logger = logging.getLogger('jpm-intel')

@app.on_event("startup")
def startup():
    engine = models.get_engine(DATABASE_URL)
    models.create_tables(engine)
    app.state.engine = engine
    app.state.websockets = set()
    # start ingest
    import app.ingest as ingest
    loop = asyncio.get_event_loop()
    loop.create_task(ingest.start_background_tasks(app))

@app.get("/")
async def index():
    return FileResponse('./static/index.html')

@app.get('/events')
def get_events(limit: int = 100):
    engine = app.state.engine
    conn = engine.connect()
    sel = text("SELECT id, source_id, title, description, event_type, timestamp, latitude, longitude, source, confidence FROM events ORDER BY timestamp DESC NULLS LAST LIMIT :limit")
    res = conn.execute(sel, {'limit': limit}).fetchall()
    conn.close()
    items = []
    for r in res:
        items.append({
            'id': str(r[0]),
            'source_id': r[1],
            'title': r[2],
            'description': r[3],
            'event_type': r[4],
            'timestamp': r[5].isoformat() if r[5] else None,
            'latitude': r[6],
            'longitude': r[7],
            'source': r[8],
            'confidence': float(r[9]) if r[9] is not None else 0.5,
        })
    return {'events': items}

@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    app.state.websockets.add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # echo for now
            await websocket.send_text(f"received: {data}")
    except WebSocketDisconnect:
        if websocket in app.state.websockets:
            app.state.websockets.remove(websocket)

# serve a very small static frontend

