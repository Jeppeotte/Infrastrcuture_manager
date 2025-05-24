from fastapi import FastAPI
from fastapi.params import Depends
from nicegui import ui
import uvicorn
from db.db_session import get_postgres_db
from db.db_operations import check_database_tables
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session

@asynccontextmanager
async def lifespan(app: FastAPI, db: Session = Depends(get_postgres_db)):
    # On startup check if the needed database tables has been created
    try:
        check_database_tables(db)
    except Exception as e:
        raise RuntimeError(f"Database tables initialization failed: {str(e)}")
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
