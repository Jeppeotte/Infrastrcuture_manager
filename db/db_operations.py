from sqlalchemy.orm import Session
from sqlalchemy import inspect, select, MetaData, Table, desc, null, text
from models.add_nodes import EdgeNode, Base, NodeConfig, NodeState, DeviceData, Trigger
from models.manage_nodes import DeviceDataSchema
from fastapi import HTTPException, status
from db.db_session import postgres_engine, timescale_engine
from sqlalchemy import Column, String, TIMESTAMP, func
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.dialects.postgresql import JSONB
import logging

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def check_database_tables(db:Session):
    # Check if all the necessary tables exist
    inspector = inspect(postgres_engine)
    tables_to_check = [EdgeNode, NodeState, DeviceData, Trigger]

    # Get existing table names from the database
    existing_tables = inspector.get_table_names()

    for table_class in tables_to_check:
        table_name = table_class.__tablename__
        if table_name not in existing_tables:
            try:
                Base.metadata.create_all(bind=db.bind, tables=[table_class.__table__])
                db.commit()
            except SQLAlchemyError as e:
                db.rollback()
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to create {table_name} table: {str(e)}"
                )

def create_edge_node(postgres_db: Session, timescale_db: Session, node_data: NodeConfig):
    # Create an edgenode
    # Check for duplicate node_id
    if postgres_db.query(EdgeNode).filter(EdgeNode.node_id == node_data.node_id).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Node ID {node_data.node_id} already exists"
        )

    try:
        # Create table for the group in TimescaleDB if needed
        ts_inspector = inspect(timescale_engine)
        group_table_name = f"{node_data.group_id}"

        if group_table_name not in ts_inspector.get_table_names():
            # Create a temporary metadata
            temp_metadata = MetaData()

            group_table = Table(
                group_table_name,
                temp_metadata,
                Column("time", TIMESTAMP(timezone=True), primary_key=True),
                Column("device_id", String, primary_key=True),
                Column("sensor_id", String, primary_key=True),
                Column("metric_value", JSONB)
            )

            # Create the table
            temp_metadata.create_all(bind=timescale_db.bind)

            # Convert to TimescaleDB hypertable
            with timescale_engine.connect() as conn:
                conn.execute(text(
                    "SELECT create_hypertable(:table_name, 'time', if_not_exists => TRUE)"
                ).bindparams(table_name=group_table_name))
                conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create group table: {str(e)}")

    try:
        # Add node to database
        # Prepare data
        db_node = EdgeNode(
            node_id=node_data.node_id,
            group_id=node_data.group_id,
            ip=node_data.ip,
            description=node_data.description,
            app_services=node_data.app_services
        )
        postgres_db.add(db_node)
        postgres_db.commit()
        postgres_db.refresh(db_node)
        return db_node

    except Exception as e:
        postgres_db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create node: {str(e)}")

def add_device_to_node(node_id: str,device: str,db: Session):
    try:
        node = db.get(EdgeNode, node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")

        # Initialize list if None
        if (device_services := node.device_services) is None:
            device_services = node.device_services = []

        if device in device_services:
            raise ValueError(f"Device '{device}' already exists for node {node_id}")

        device_services.append(device)
        return f"Device {device} added to node {node_id}"

    except Exception as e:
        raise ValueError(f"Error adding device: {str(e)}") from e

def get_all_nodes(db: Session):
    # Get all nodes
    # Select statement - Selecting the Edgenode model
    stmt = select(EdgeNode)

    return list(db.scalars(stmt))


def get_specific_node(node_id:str, db: Session):
    # Get specific node
    # Select statement - Selecting the Edgenode model
    stmt = select(EdgeNode).where(EdgeNode.node_id == node_id)

    node = db.scalar(stmt)

    if not node:
        raise HTTPException(status_code=404, detail=f"Node not found")
    return node

def get_latest_node_state(db: Session):
    # Get each node latest statement from device_states
    stmt = (
        select(
            NodeState.node_id,
            NodeState.time,
            NodeState.state
        )
        .where(NodeState.device_id.is_(None))  # Proper NULL check
        .distinct(NodeState.node_id)  # Get one record per node
        .order_by(
            NodeState.node_id,
            NodeState.time.desc()  # Most recent first
        )
    )
    latest_rows = db.execute(stmt)

    result = {}
    for node_id, time, state in latest_rows:
        result[node_id] = {"time": time.timestamp(), "state": state}
    return result

def insert_device_data(device_data: DeviceDataSchema, db: Session):
    try:

        # Check for existing device more efficiently
        exists = db.query(DeviceData).filter(
            DeviceData.group_id == device_data['group_id'],
            DeviceData.node_id == device_data['node_id'],
            DeviceData.device_id == device_data['device_id'],
            DeviceData.protocol_type == device_data['protocol_type']
        ).first() is not None

        if exists:
            raise ValueError("Device already exists")

        db.add(DeviceData(**device_data))
        return f"Device {device_data['device_id']} prepared for insertion"

    except IntegrityError as e:
        raise ValueError(f"Database integrity error: {str(e)}") from e
    except Exception as e:
        raise ValueError(f"Database error: {str(e)}") from e

def insert_trigger_data(triggers: list, db: Session):
    try:
        db.execute(Trigger.__table__.insert(), triggers)
        return f"Triggers prepared for insertion"

    except Exception as e:
        db.rollback()
        return f"Database error: {str(e)}"


def get_device_data(node_id: str, db: Session):
    # Get all devices for the node
    devices = db.query(DeviceData).filter(DeviceData.node_id == node_id).all()

    # If there are no devices return empty list
    if not devices:
        return []

    # Get latest DBIRTH or DDEATH state for each device
    stmt = (
        select(
            NodeState.device_id,
            NodeState.state,
            NodeState.time
        )
        .where(
            (NodeState.node_id == node_id) &
            (NodeState.message_type.in_(['DBIRTH', 'DDEATH']))
        )
        .distinct(NodeState.device_id)
        .order_by(
            NodeState.device_id,
            NodeState.time.desc()  # Most recent first per device
        )
    )

    latest_states = db.execute(stmt).all()
    state_map = {device_id: (state, time) for device_id, state, time in latest_states}

    # Prepare results with raw state values
    results = []
    for device in devices:
        state_info = state_map.get(device.device_id, (None, None))

        results.append({
            "group_id": device.group_id,
            "node_id": device.node_id,
            "device_id": device.device_id,
            "alias": device.alias,
            "manufacturer": device.manufacturer,
            "model": device.model,
            "protocol_type": device.protocol_type,
            "state": state_info[0] if state_info[0] is not None else None,
            "last_updated": state_info[1].isoformat() if state_info[1] else "-",
            "device_ip": device.device_ip,
            "device_port": device.device_port
        })
    return results

def get_triggers(node_id: str, db: Session):
    # Get all the triggers on the node
    stmt = select(Trigger).where(Trigger.node_id == node_id)
    triggers = db.execute(stmt).scalars().all()
    # Turns it into a list of dictionaries
    result = [t.to_dict() for t in triggers]
    return result

def delete_node(node_id: str, db: Session):
    # Delete the node
    try:
        with db.begin():
            devices_deleted = db.query(DeviceData).filter(DeviceData.node_id == node_id).delete()
            triggers_deleted = db.query(Trigger).filter(Trigger.node_id == node_id).delete()
            edge_nodes_deleted = db.query(EdgeNode).filter(EdgeNode.node_id == node_id).delete()

            return f"Successfully deleted edge node {node_id} and its devices from the database"

    except SQLAlchemyError as e:
        db.rollback()
        raise SQLAlchemyError(f"Failed to delete node {node_id}: {str(e)}")

def delete_device(device_id: str, node_id: str, db: Session):
    try:
        with db.begin():
            db.query(DeviceData).filter(
                DeviceData.device_id == device_id,
                DeviceData.node_id == node_id
            ).delete()

            db.query(Trigger).filter(
                Trigger.device_id == device_id,
                Trigger.node_id == node_id
            ).delete()

            # Get the node
            node = db.get(EdgeNode, node_id)

            # Remove device if it exists
            if device_id in node.device_services:
                node.device_services.remove(device_id)

            return f"Successfully deleted device:{device_id} frome node:{node_id}"

    except SQLAlchemyError as e:
        db.rollback()
        raise SQLAlchemyError(f"Failed to delete device: {device_id} from node: {node_id}: {str(e)}")
