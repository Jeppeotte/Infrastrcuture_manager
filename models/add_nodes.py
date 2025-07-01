from sqlalchemy.ext.mutable import MutableList
from sqlalchemy import Column, String, TIMESTAMP, Integer, DateTime, func
from sqlalchemy.inspection import inspect
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from db.db_session import Base
from pydantic import BaseModel

# Define the structure for configuring the edge node
class NodeConfig(BaseModel):
    group_id: str
    node_id: str
    description: str | None = None
    ip: str
    app_services: list[str] = []

#Database class for the edge nodes
class EdgeNode(Base):
    __tablename__ = "edge_nodes"

    node_id = Column(String, primary_key=True, index=True)
    group_id = Column(String)
    description = Column(String)
    ip = Column(String)
    app_services = Column(MutableList.as_mutable(ARRAY(String)))
    device_services = Column(MutableList.as_mutable(ARRAY(String)), nullable=True)

# Node states for the database
class NodeState(Base):
    __tablename__ = "device_states"

    time = Column(TIMESTAMP(timezone=True), primary_key=True, index=True)
    node_id = Column(String, primary_key=True, index=True)
    device_id = Column(String, nullable=True)
    message_type = Column(String, primary_key=True, index=True)
    state_key = Column(String)
    state = Column(String)

# Device information for database
class DeviceData(Base):
    __tablename__ = "devices"

    group_id = Column(String, primary_key=True, index=True)
    node_id = Column(String, primary_key=True, index=True)
    device_id = Column(String, primary_key=True, index=True)
    alias = Column(String, nullable=True)
    manufacturer = Column(String, nullable=True)
    model = Column(String, nullable=True)
    protocol_type = Column(String, primary_key=True, index=True)
    device_ip = Column(String, nullable=True)
    device_port = Column(Integer, nullable=True)

class Trigger(Base):
    __tablename__ = "triggers"

    trigger_id = Column(Integer, primary_key=True)
    trigger_type = Column(String)
    node_id = Column(String)
    device_id = Column(String)
    topic = Column(String)
    source = Column(JSONB)
    condition = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    def to_dict(self):
        return {c.key: getattr(self, c.key)
                for c in inspect(self).mapper.column_attrs}

