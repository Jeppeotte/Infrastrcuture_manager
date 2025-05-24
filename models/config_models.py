from pydantic import BaseModel

# General models
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

class DeviceServiceTestParameters(BaseModel):
    configfile_path: str

class PollingInterval(BaseModel):
    default_interval: float | None = 1.0
    data_interval: float  | None = None
    data_trigger: float  | None = None
    process_trigger: float | None = None

# Modbus specific models
class ModbusPollingInterval(BaseModel):
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

class ModbusDeviceServiceConfig(BaseModel):
    device: Device
    polling: ModbusPollingInterval
    holding_registers: list[HoldingRegisters] | None = None
    coils: list[Coils] | None = None

#S7comm specific models
class Triggers(BaseModel):
    trigger_type: str
    node_id: str
    device_id: str
    topic: str
    source: dict
    condition: str

class S7commVariables(BaseModel):
    name: str
    data_type:str
    byte_offset: int
    bit_offset: int
    units: str

class DataBlock(BaseModel):
    name: str
    db_number: int
    read_size: int
    byte_offset: int
    variables: list[S7commVariables]

class S7CommDeviceServiceConfig(BaseModel):
    device: Device
    polling: PollingInterval
    triggers: list[Triggers]
    data_block: DataBlock | None = None

