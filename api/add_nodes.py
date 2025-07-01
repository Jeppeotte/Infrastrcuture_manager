from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy.orm import Session
from models.add_nodes import NodeConfig
from db.db_session import get_db
from db.db_operations import create_edge_node

router = APIRouter(prefix="/api/add_nodes")


@router.get("/configurations")
async def get_configurations():
    #Get possible configuration such as already existing group IDs

    return None

@router.post("/create_node")
async def create_node(config: NodeConfig, db: Session = Depends(get_db)):
    #Connect to the db and insert the information about the new node
    try:
        # Add the node information to the table edge_nodes
        new_node = create_edge_node(db, config)
        return {"status": "success", "node_id": new_node.node_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


