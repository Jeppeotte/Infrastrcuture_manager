from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy.orm import Session
from db.db_session import get_db
from db.db_operations import get_all_nodes, get_latest_node_state
from models.add_nodes import Trigger
import db.db_operations as db_op
from pydantic import BaseModel
from models.manage_nodes import AddDeviceSchema
import logging

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class Device(BaseModel):
    group_id: str
    node_id: str
    device_id: str
    alias: str | None = None
    manufacturer: str
    model: str
    protocol_type: str
    ip: str
    port: int
    unit_id: int | None = None
    rack: int | None = None
    slot: int | None = None

class PollingInterval(BaseModel):
    default_coil_interval: float
    default_register_interval: float

class HoldingRegisters(BaseModel):
    name: str
    address: int
    data_type: str
    units: str

class Coils(BaseModel):
    name: str
    address: int

class DeviceServiceTestParameters(BaseModel):
    configfile_path: str



router = APIRouter(prefix="/api/manage_nodes")

@router.get("/get_all_nodes")
async def get_all_nodes_info(db: Session = Depends(get_db)):
    #Get all nodes from the database

    return get_all_nodes(db)

@router.get("/get_node_state")
async def get_node_state(db: Session = Depends(get_db)):
    # Get the latest state of the nodes
    return get_latest_node_state(db)

@router.post("/activate_device_service")
async def activate_device_service():
    #After the device service has been added it has to be activated/started
    #Activating the device service through spinning up the container or script

    return


@router.get("/{node_id}")
async def get_node_details(node_id: str, db: Session = Depends(get_db)):
    try:
        #logger.debug(f"Fetching data for node {node_id}")

        node_data = db_op.get_specific_node(node_id, db)
        #logger.debug(f"Node data: {node_data}")

        device_data = db_op.get_device_data(node_id, db)
        #logger.debug(f"Device data: {len(device_data)} devices")

        triggers_data = db_op.get_triggers(node_id, db)
        #logger.debug(f"Triggers data: {len(triggers_data)} triggers")

        return {
            "node_data": node_data,
            "device_data": device_data,
            "triggers_data": triggers_data
        }
    except Exception as e:
        #logger.error(f"Error in get_node_details: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add_devicedata_db")
async def add_devicedata_db(request: AddDeviceSchema, db: Session = Depends(get_db)):
    try:
        with db.begin():  # Transaction context manager
            #Add to edge_nodes
            db_op.add_device_to_node(request.device_data.node_id, request.device_data.device_id, db)

            #Add to devices
            db_op.insert_device_data(request.device_data.model_dump(), db)

            #Bulk insert triggers
            trigger_dicts = [trigger.model_dump() for trigger in request.triggers]
            db.execute(Trigger.__table__.insert(), trigger_dicts)

        return {"status": "success"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail={
            "error": "Validation Error",
            "message": str(e)
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error": "Server Error",
            "message": f"Server error: {str(e)}"
        })

@router.post("/delete_node")
async def delete_node(node_id: str, db: Session = Depends(get_db)):
    #Delete the edge node and all its devices from the database
    #Remeber to delete triggers from triggers table
    try:
        status = db_op.delete_node(node_id, db)

        return status

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/delete_device")
async def delete_device(node_id:str, device_id: str, db: Session = Depends(get_db)):
    # Delete a specific device on an edge node and its triggers
    try:
        status = db_op.delete_device(device_id, node_id, db)

        return status

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))