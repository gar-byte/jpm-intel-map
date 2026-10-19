from sqlalchemy import create_engine, Table, Column, String, Float, MetaData, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

metadata = MetaData()

events = Table(
    'events',
    metadata,
    Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column('source_id', String, unique=True, nullable=False),
    Column('title', String),
    Column('description', Text),
    Column('event_type', String),
    Column('timestamp', DateTime(timezone=True)),
    Column('latitude', Float),
    Column('longitude', Float),
    Column('source', String),
    Column('confidence', Float, default=0.5),
)

def get_engine(database_url):
    return create_engine(database_url)

def create_tables(engine):
    metadata.create_all(engine)
