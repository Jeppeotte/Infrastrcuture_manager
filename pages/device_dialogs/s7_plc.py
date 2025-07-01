from nicegui import ui
from typing import List, Dict, Any
from .base_dialog import BaseDeviceDialog


class S7PlcDialog(BaseDeviceDialog):
    def __init__(self, node_id, node_ip, group_id, device_id, device_to_topic):
        super().__init__("PLC", "S7Comm", node_id, node_ip, group_id, device_id, device_to_topic)
        self.variables: List[Dict] = []
        self.triggers: List[Dict] = []
        self.data_block_info = None

    def render_content(self):
        #Render S7Comm PLC configuration dialog
        self._render_connection_config()
        self._render_process_monitoring()
        self._render_data_trigger()
        self._render_polling_config()

    def _render_connection_config(self):
        ui.label('S7COMM CONNECTION CONFIGURATION').classes('text-lg font-bold text-gray-500')
        with ui.grid(columns=1).classes('w-full'):
            self.plc_ip = ui.input(label="Device ip")
            self.plc_port = ui.number(value=102, min=1, max=65535, label="Device port")
            self.rack = ui.number(value=0, min=0, label="Device Rack")
            self.slot = ui.number(value=1, min=0, label="Device slot")

    def _render_process_monitoring(self):
        with ui.column().classes('gap-0'):
            ui.label('S7COMM PROCESS MONITORING CONFIGURATION').classes('text-lg font-bold text-gray-500 mt-6')
            ui.label('Monitors the state of the process').classes('text-base font-bold text-gray-500')
            ui.label('Trigger type: process trigger').classes('text-base font-bold text-gray-500')

        ui.label('Source configuration:').classes('text-base font-bold text-gray-500')

        with ui.grid(columns=1).classes('w-full'):
            self.process_monitoring_variable_type = ui.select(options=['Memory bit', 'Boolean variable'],
                                                              label='Variable type')
            self.process_monitoring_name = ui.input(value='Process_trigger', label='Trigger name')
            self.process_monitoring_block = ui.number(value=0, min=0,label='Data block')
            self.process_monitoring_byte = ui.number(value=0, min=0,label='Byte offset')
            self.process_monitoring_bit = ui.number(value=0, min=0,label='Bit offset')
            self.process_bool_index = ui.number(value=0, min=0, label='Bool index')

        ui.label('Condition configuration:').classes('text-base font-bold text-gray-500')
        with ui.grid(columns=2).classes('w-full'):
            ui.label('Condition:').classes('font-semibold')
            self.process_monitoring_condition = ui.select(
                options=['True', 'False'],
                label='When source is == condition, begin sampling',
                value='True'
            )

    def _render_data_trigger(self):
        with ui.column().classes('gap-0'):
            ui.label('S7COMM DATA CONFIGURATION').classes('text-lg font-bold text-gray-500 mt-6')
            self.data_trigger_checkbox = ui.checkbox(text='Include')

        self.data_trigger_container = ui.column().bind_visibility_from(self.data_trigger_checkbox, 'value')
        with self.data_trigger_container:
            ui.label('Data trigger: Monitors when to start data sampling').classes('text-base font-bold text-gray-500')
            ui.label('Source configuration:').classes('text-base font-bold text-gray-500')
            with ui.grid(columns=1).classes('w-full'):
                self.trigger_name = ui.input(value="Data_trigger", label="Trigger name")
                self.trigger_datatype = ui.select(['Bool'], value='Bool', label="Data type")
                self.trigger_block = ui.number(value=0, min=0, label="Data block")
                self.trigger_byte = ui.number(value=0, min=0, label="Byte offset")
                self.trigger_bit = ui.number(value=0, min=0, label="Bit offset")

            ui.label('Condition configuration:').classes('text-base font-bold text-gray-500')
            with ui.grid(columns=1).classes('w-full'):
                self.trigger_condition = ui.select(
                    options=['True', 'False'],
                    label='When source is == condition, begin sampling',
                    value='True'
                )

            ui.label('Variables to monitor').classes('text-base font-bold text-gray-500')
            with ui.grid(columns=2).classes('w-full mt-2'):
                ui.label('Data name:').classes('font-semibold')
                self.data_name = ui.input(value='ProductionData')
                ui.label('Data block:').classes('font-semibold')
                self.data_block = ui.number(value=0, min=0)

            self.variables_container = ui.column().classes('w-full space-y-4 mt-4')
            self.variables = []

            with ui.row().classes('w-full justify-end mt-4'):
                ui.button('Add Data Variable', icon='add', on_click=self.add_variable).props('outline')

    def _render_polling_config(self):
        ui.label('S7COMM POLLING CONFIGURATION').classes('text-lg font-bold text-gray-500 mt-6')
        with ui.grid(columns=2).classes('w-full'):
            ui.label('Default interval (s):').classes('font-semibold')
            self.default_interval = ui.number(value=1.0, min=0.1, max=5.0, step=0.1, format='%.1f')
            ui.label('Process monitoring interval (s):').classes('font-semibold')
            self.process_interval = ui.number(value=1.0, min=0.1, max=2.0, step=0.1, format='%.1f')
            ui.label('Data trigger interval (s):').classes('font-semibold')
            self.trigger_interval = ui.number(value=1.0, min=0.1, max=2.0, step=0.1, format='%.1f')
            ui.label('Data sampling interval (s):').classes('font-semibold')
            self.data_interval = ui.number(value=1.0, min=0.1, max=2.0, step=0.1, format='%.1f')

    def add_variable(self, name="", data_type="Real", byte_offset=0, bit_offset=0, units=""):
        with self.variables_container:
            with ui.card().classes('w-full p-4 bg-gray-50 hover:bg-gray-100') as card:
                with ui.grid(columns=2).classes('w-full gap-4'):
                    ui.label('Variable name:').classes('font-semibold')
                    name_input = ui.input(value=name)
                    ui.label('Data type:').classes('font-semibold')
                    type_input = ui.select(['Bool', 'Int', 'Real'], value=data_type)
                    ui.label('Byte offset:').classes('font-semibold')
                    byte_input = ui.number(value=byte_offset, min=0)
                    ui.label('Bit offset:').classes('font-semibold')
                    bit_input = ui.number(value=bit_offset, min=0, max=7)
                    ui.label('Units:').classes('font-semibold')
                    units_input = ui.input(value=units)

                    with ui.row().classes('col-span-2 justify-end'):
                        ui.button('Remove', on_click=lambda c=card: self.remove_variable(c)) \
                            .props('flat dense color=negative')

        self.variables.append({
            'card': card,
            'inputs': {
                'name': name_input,
                'type': type_input,
                'byte_offset': byte_input,
                'bit_offset': bit_input,
                'units': units_input
            }
        })

    def remove_variable(self, card):
        self.variables[:] = [v for v in self.variables if v['card'] != card]
        card.delete()

    def get_config(self):
        # Build and return the S7Comm configuration dictionary
        self._build_data_block_info()
        self._build_triggers()

        config = {
            "device": {
                "group_id": self.group_id,
                "node_id": self.node_id,
                "device_id": self.device_id.value,
                "protocol_type": self.protocol,
                "ip": self.plc_ip.value,
                "port": self.plc_port.value,
                "rack": self.rack.value,
                "slot": self.slot.value
            },
            "polling": {
                "default_interval": self.default_interval.value,
                "data_interval": self.trigger_interval.value,
                "data_trigger": self.data_interval.value,
                "process_trigger": self.process_interval.value
            },
            "triggers": self.triggers,
            "data_block": self.data_block_info
        }

        return config

    def _build_data_block_info(self):
        if self.variables:
            byte_offsets = [var['inputs']['byte_offset'].value for var in self.variables]
            data_types = [var['inputs']['type'].value for var in self.variables]

            min_offset = min(byte_offsets)
            max_offset = max(byte_offsets)
            read_size = max_offset - min_offset

            if 'Real' in data_types or 'DWord' in data_types:
                read_size += 4
            elif 'Word' in data_types or 'Int' in data_types:
                read_size += 2
            else:
                read_size += 1

            if read_size <= 0:
                raise ValueError("Please add at least one variable")

            self.data_block_info = {
                "name": self.data_name.value,
                "db_number": self.data_block.value,
                "read_size": read_size,
                "byte_offset": min_offset,
                "variables": [{
                    "name": var['inputs']['name'].value,
                    "data_type": var['inputs']['type'].value,
                    "byte_offset": var['inputs']['byte_offset'].value,
                    "bit_offset": var['inputs']['bit_offset'].value,
                    "units": var['inputs']['units'].value
                } for var in self.variables]
            }

    def _build_triggers(self):
        # Process monitoring trigger
        monitoring = {
            "trigger_type": "process_trigger",
            "node_id": self.node_id,
            "device_id": self.device_id.value,
            "topic": f"spBv1.0/{self.group_id}/STATE/{self.node_id}/{self.device_id.value}",
            "source": {
                "variable_type": self.process_monitoring_variable_type.value,
                "db_number": self.process_monitoring_block.value,
                "name": self.process_monitoring_name.value,
                "read_size": 1,
                "data_type": "Bool",
                "byte_offset": self.process_monitoring_byte.value,
                "bit_offset": self.process_monitoring_bit.value,
                "bool_index": self.process_bool_index.value,
                "units": "None"
            },
            "condition": self.process_monitoring_condition.value
        }
        self.triggers.append(monitoring)

        # Data trigger (if enabled)
        if self.data_trigger_checkbox.value:
            data_trigger = {
                "trigger_type": "data_trigger",
                "node_id": self.node_id,
                "device_id": self.device_id.value,
                "topic": f"spBv1.0/{self.group_id}/STATE/{self.node_id}/{self.device_id.value}",
                "source": {
                    "db_number": self.trigger_block.value,
                    "name": self.trigger_name.value,
                    "read_size": 1,
                    "data_type": self.trigger_datatype.value,
                    "byte_offset": self.trigger_byte.value,
                    "bit_offset": self.trigger_bit.value,
                    "units": "None"
                },
                "condition": self.trigger_condition.value
            }
            self.triggers.append(data_trigger)

    def get_device_data(self):
        return {
            "group_id": self.group_id,
            "node_id": self.node_id,
            "device_id": self.device_id.value,
            "protocol_type": self.protocol,
            "ip": self.plc_ip.value,
            "port": self.plc_port.value
        }