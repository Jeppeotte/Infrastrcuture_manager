from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

#Relational DB connection
POSTGRESQL_URL = "postgresql://postgres:admin@localhost:5432/relationdata"

#Time series data connection
TIMESCALE_URL = "postgresql://postgres:admin@localhost:5433/devicedata"

Base = declarative_base()

postgres_engine = create_engine(POSTGRESQL_URL)
postgres_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=postgres_engine)

timescale_engine = create_engine(TIMESCALE_URL)
timescale_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=timescale_engine)

def get_postgres_db():
    db: Session = postgres_SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_timescale_db():
    db: Session = timescale_SessionLocal()
    try:
        yield db
    finally:
        db.close()