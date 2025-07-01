from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

#Timescale database url
db_url = "postgresql://postgres:admin@localhost:5432/postgres"

Base = declarative_base()

db_engine = create_engine(db_url)
db_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

def get_db():
    db: Session = db_SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        logger.error("Database error occurred")
        raise
    finally:
        db.close()
