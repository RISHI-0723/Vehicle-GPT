"""Database configuration and session management."""
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

from app.core.config import settings, DEMO_VEHICLE_CONFIG

logger = logging.getLogger(__name__)

# Create engine based on database URL
# For SQLite, we need special handling for file-based vs in-memory databases
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite requires special connect_args for proper threading
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=settings.DEBUG,
    )
else:
    engine = create_engine(settings.DATABASE_URL, echo=settings.DEBUG)


# Enable foreign keys for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key constraints for SQLite connections."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for getting database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database and seed demo vehicle."""
    from app.db.models import Vehicle, Telemetry, Simulation

    logger.info("Initializing database...")

    # Create all tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")

    # Seed demo vehicle if not exists
    db = SessionLocal()
    try:
        existing = db.query(Vehicle).filter(
            Vehicle.vehicle_id == DEMO_VEHICLE_CONFIG["vehicle_id"]
        ).first()

        if not existing:
            demo_vehicle = Vehicle(**DEMO_VEHICLE_CONFIG)
            db.add(demo_vehicle)
            db.commit()
            logger.info(f"Demo vehicle {DEMO_VEHICLE_CONFIG['vehicle_id']} created.")
        else:
            logger.info(f"Demo vehicle {DEMO_VEHICLE_CONFIG['vehicle_id']} already exists.")
    finally:
        db.close()

    logger.info("Database initialization complete.")
