from fastapi import FastAPI
from nicegui import ui
import uvicorn
from db.db_session import get_db
from db.db_operations import check_database_tables
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import sys
import logging


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup check if the needed database tables has been created
    try:
        db = next(get_db())  # Get fresh DB session
        check_database_tables(db)
        logger.info("Database verified successfully")
    except SQLAlchemyError as e:
        logger.critical(f"Database connection failed: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Unexpected startup error: {str(e)}")
        sys.exit(1)
    yield

# Initialize FastAPI
app = FastAPI(lifespan=lifespan)

# Import all API routers
from api.dashboard import router as dashboard_router
from api.add_nodes import router as add_nodes_router
from api.manage_nodes import router as manage_nodes_router
from api.data_saver import router as data_saver_router

app.include_router(dashboard_router)
app.include_router(add_nodes_router)
app.include_router(manage_nodes_router)
app.include_router(data_saver_router)

# Import all pages
from pages import dashboard, add_nodes, manage_nodes, node_page

# Run Both FastAPI and NiceGUI Together
if __name__ == "__main__":
    ui.run_with(
        app,
        mount_path="/",
        title="Edge Node Manager"
    )
    uvicorn.run(app, host="0.0.0.0", port=8000)

