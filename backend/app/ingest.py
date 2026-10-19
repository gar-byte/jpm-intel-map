import asyncio
import aiohttp
import feedparser
import json
from datetime import datetime, timezone

USGS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
# Example RSS feed (BBC World)
RSS_URL = "http://feeds.bbci.co.uk/news/world/rss.xml"

async def fetch_json(session, url):
    async with session.get(url) as resp:
        return await resp.json()

async def fetch_text(session, url):
    async with session.get(url) as resp:
        return await resp.text()

async def poll_usgs(app):
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                data = await fetch_json(session, USGS_URL)
                features = data.get('features', [])
                for f in features:
                    sid = f.get('id')
                    props = f.get('properties', {})
                    geom = f.get('geometry', {})
                    coords = geom.get('coordinates', [None, None])
                    title = props.get('title')
                    ts = props.get('time')
                    if ts:
                        ts = datetime.fromtimestamp(ts/1000.0, tz=timezone.utc)
                    desc = props.get('detail') or props.get('title')
                    lat = coords[1]
                    lon = coords[0]
                    event = dict(
                        source_id = f"usgs:{sid}",
                        title = title,
                        description = desc,
                        event_type = 'earthquake',
                        timestamp = ts,
                        latitude = lat,
                        longitude = lon,
                        source = 'usgs',
                        confidence = 0.9,
                    )
                    await upsert_event(app, event)
            except Exception as e:
                app.logger and app.logger.error(f"USGS poll error: {e}")
            await asyncio.sleep(60)

async def poll_rss(app):
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                text = await fetch_text(session, RSS_URL)
                feed = feedparser.parse(text)
                for entry in feed.entries[:10]:
                    sid = entry.get('id') or entry.get('link')
                    title = entry.get('title')
                    desc = entry.get('summary')
                    # Very naive location extraction: none — store without coords
                    event = dict(
                        source_id = f"rss:{sid}",
                        title = title,
                        description = desc,
                        event_type = 'news',
                        timestamp = datetime.now(timezone.utc),
                        latitude = None,
                        longitude = None,
                        source = 'bbc-rss',
                        confidence = 0.5,
                    )
                    await upsert_event(app, event)
            except Exception as e:
                app.logger and app.logger.error(f"RSS poll error: {e}")
            await asyncio.sleep(120)

async def upsert_event(app, event):
    # Insert if source_id not exists; simple dedupe
    engine = app.state.engine
    conn = engine.connect()
    sel = f"SELECT id FROM events WHERE source_id = :source_id"
    res = conn.execute(sel, {'source_id': event['source_id']}).fetchone()
    if not res:
        ins = (
            "INSERT INTO events (source_id, title, description, event_type, timestamp, latitude, longitude, source, confidence) "
            "VALUES (:source_id, :title, :description, :event_type, :timestamp, :latitude, :longitude, :source, :confidence) RETURNING id"
        )
        params = {
            'source_id': event['source_id'],
            'title': event['title'],
            'description': event['description'],
            'event_type': event['event_type'],
            'timestamp': event['timestamp'],
            'latitude': event['latitude'],
            'longitude': event['longitude'],
            'source': event['source'],
            'confidence': event['confidence'],
        }
        try:
            r = conn.execute(ins, params)
            conn.commit()
            new_id = r.fetchone()[0]
            # broadcast via websocket
            await broadcast_event(app, new_id)
        except Exception as e:
            app.logger and app.logger.error(f"Insert event error: {e}")
    conn.close()

async def broadcast_event(app, event_id):
    # Fetch event and send to connected websocket clients
    engine = app.state.engine
    conn = engine.connect()
    sel = "SELECT id, source_id, title, description, event_type, timestamp, latitude, longitude, source, confidence FROM events WHERE id = :id"
    r = conn.execute(sel, {'id': event_id}).fetchone()
    conn.close()
    if not r:
        return
    event = dict(
        id = str(r[0]),
        source_id = r[1],
        title = r[2],
        description = r[3],
        event_type = r[4],
        timestamp = r[5].isoformat() if r[5] else None,
        latitude = r[6],
        longitude = r[7],
        source = r[8],
        confidence = float(r[9]) if r[9] is not None else 0.5,
    )
    message = json.dumps({'type':'event','event': event})
    # Send to websockets
    websockets = list(app.state.websockets)
    for ws in websockets:
        try:
            await ws.send_text(message)
        except Exception:
            try:
                await ws.close()
            except Exception:
                pass
            if ws in app.state.websockets:
                app.state.websockets.remove(ws)

async def start_background_tasks(app):
    app.logger and app.logger.info('Starting background ingest tasks...')
    app.state.usgs_task = asyncio.create_task(poll_usgs(app))
    app.state.rss_task = asyncio.create_task(poll_rss(app))

