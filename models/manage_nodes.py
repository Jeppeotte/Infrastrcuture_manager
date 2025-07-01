from pydantic import BaseModel
from typing import Optional
from pydantic import field_validator, Field, ConfigDict


class DeviceDataSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)  # Auto-strip strings

    group_id: str = Field(min_length=1)
    node_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1)  # Ensures non-empty string
    protocol_type: str = Field(min_length=1)
    alias: Optional[str] = Field(None, min_length=1)  # If provided, must be non-empty
    manufacturer: Optional[str] = Field(None, min_length=1)
    model: Optional[str] = Field(None, min_length=1)
    device_ip: Optional[str] = Field(None, pattern=r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    device_port: Optional[int] = Field(None, ge=1, le=65535)

    @field_validator('*')
    def reject_empty_strings(cls, v):
        if isinstance(v, str) and not v.strip():
            raise ValueError("String cannot be empty or whitespace only")
        return v


class TriggerSchema(BaseModel):
    trigger_type: str = Field(min_length=1)
    node_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    source: dict = Field(min_length=1)  # Ensures non-empty dict
    condition: str = Field(min_length=1)

class AddDeviceSchema(BaseModel):
    device_data: DeviceDataSchema
    triggers: list[TriggerSchema]