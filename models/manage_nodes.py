from pydantic import BaseModel
from typing import Optional, List

class DeviceDataSchema(BaseModel):
    group_id: str
    node_id: str
    device_id: str
    protocol_type: str
    alias: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    device_ip: Optional[str] = None
    device_port: Optional[int] = None

class TriggerSchema(BaseModel):
    trigger_type: str
    node_id: str
    device_id: str
    topic: str
    source: dict
    condition: str

class AddDeviceSchema(BaseModel):
    device_data: DeviceDataSchema
    triggers: list[TriggerSchema]