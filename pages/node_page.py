import time
from nicegui import ui
from pages.layout import create_layout
import httpx
from models.config_models import  S7CommDeviceServiceConfig
from datetime import datetime

@ui.page("/manage_nodes/{node_id}")
async def node_manager(node_id: str):
    create_layout()
    # Fetch node data from API
    async def fetch_node_data():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://localhost:8000/api/manage_nodes/{node_id}")
                if response.status_code == 200:
                    return response.json()
                else:
                    ui.notify(f"Failed to fetch node data: {response.text}", type='negative')
                    return None
        except Exception as e:
            ui.notify(f"Error fetching node: {str(e)}", type='negative')
            return None

    data = await fetch_node_data()
    node_data = data["node_data"]
    device_services = data["device_data"]
    trigger_data = data["triggers_data"]
    if trigger_data:
        # Extract device_ids where trigger_type is data_trigger
        data_trigger_device_ids = [
            trigger["device_id"]
            for trigger in trigger_data
            if trigger.get("trigger_type") == "data_trigger"
        ]
        # Get each device id and topic for config
        device_to_topic = {
            trigger["device_id"]: trigger.get("topic", "")
            for trigger in trigger_data
            if trigger.get("trigger_type") == "data_trigger"
        }


    if not node_data:
        ui.label("Failed to load node data").classes('text-red-500')
        return

    # Variables:
    node_id = node_data['node_id']
    group_id = node_data['group_id']
    description = node_data['description']
    node_ip = node_data['ip']

    # Basic Information Section
    ui.label(f"Managing Node: {node_id}").classes('text-2xl font-bold mb-4')

    # Add this row for node actions
    with ui.row().classes('w-full justify-between items-center mb-4'):
        with ui.grid(columns=2).classes('w-full gap-4'):
            ui.label("ID:").classes('font-semibold')
            ui.label(node_id)

            ui.label("Group:").classes('font-semibold')
            ui.label(group_id)

            ui.label("Description:").classes('font-semibold')
            ui.label(description)

            ui.label("IP Address:").classes('font-semibold')
            ui.label(node_ip)

        # Delete node function
        async def delete_node_action():
            try:
                # Show spinner
                spinner = ui.spinner(size='2em')
                spinner.visible = True

                # Configure timeout - 30 seconds total, 30 seconds connect
                node_timeout = httpx.Timeout(30.0, connect=30.0)
                backend_timeout = httpx.Timeout(60.0, connect=10.0)

                # First try to delete information on the node (with shorter timeout)
                node_deletion_successful = False
                try:
                    async with httpx.AsyncClient(timeout=node_timeout) as client:
                        node_response = await client.post(f"http://{node_ip}:8000/api/configure_node/delete_node")
                        if node_response.status_code == 200:
                            node_deletion_successful = True
                        else:
                            ui.notify(f"Node responded but with error: {node_response.text}", type='warning')
                except (httpx.ConnectTimeout, httpx.ReadTimeout):
                    ui.notify("Could not connect to node within 30 seconds - proceeding with backend deletion",
                              type='warning')
                except Exception as e:
                    ui.notify(f"Error communicating with node: {str(e)}", type='warning')

                # Second delete information about the node inside the db (regardless of node deletion result)
                try:
                    async with httpx.AsyncClient(timeout=backend_timeout) as client:
                        response = await client.post(
                            "http://localhost:8000/api/manage_nodes/delete_node",
                            params={"node_id": node_id}
                        )
                        if response.status_code == 200:
                            if node_deletion_successful:
                                ui.notify(f"Successfully deleted node {node_id}", type='positive')
                            else:
                                ui.notify(f"Deleted node {node_id} from backend but couldn't confirm node deletion",
                                          type='warning')
                            ui.navigate.to("/manage_nodes")
                        else:
                            ui.notify(f"Failed to delete node from backend: {response.text}", type='negative')
                except Exception as e:
                    ui.notify(f"Error deleting node from backend: {str(e)}", type='negative')
            finally:
                spinner.visible = False

        with ui.dialog() as confirm_node_dialog:
            with ui.card():
                ui.label(f"WARNING: This will delete gateway: {node_id}!")
                with ui.row():
                    ui.button('Cancel', on_click=confirm_node_dialog.close)
                    ui.button('DELETE GATEWAY', color='red', on_click=lambda: delete_node_action())

        ui.button('Delete gateway', color='red', icon='delete', on_click=confirm_node_dialog.open).classes('self-end').props('outline')

    # Device Services Section
    ui.label("Device Services").classes('text-xl font-bold')

    # Service dialog component
    def create_device_service_dialog(device: dict):
        with ui.dialog().classes('w-full max-w-4xl').props('persistent')  as dialog:
            with ui.card().classes('w-full max-h-[80vh] overflow-y-auto p-6'):
                # Header with close button
                with ui.row().classes('w-full items-center justify-between mb-6'):
                    ui.label(f"Service: {device["device_id"]}").classes('text-2xl font-bold')
                    ui.button(icon='close', on_click=dialog.close).props('flat dense')
                with ui.grid(columns=2).classes('gap-2 w-full'):
                    # Delete the device service
                    async def delete_device_service():
                        try:
                            # Show spinner
                            spinner = ui.spinner(size='2em')
                            spinner.visible = True

                            # Configure timeout (e.g., 300 seconds = 5 minutes)
                            timeout = httpx.Timeout(300.0, connect=10.0)

                            async with httpx.AsyncClient(timeout=timeout) as client:
                                #First try to delete on node
                                node_response = await  client.post(f"http://{node_ip}:8000/api/add_devices/delete_device_service",
                                                                   params={"device_id": device['device_id']})

                                if node_response.status_code != 200:
                                    ui.notify(f"Failed to connect to node and delete device: {node_response.text}", type='negative')
                                    raise node_response.text

                                response = await client.post(
                                    f"http://localhost:8000/api/manage_nodes/delete_device",
                                    params={"node_id": node_id,"device_id": device['device_id']})
                                if response.status_code == 200:
                                    dialog.close()
                                    # Refresh the page to show updated list
                                    ui.notify(f"Successfully deleted device {device['device_id']}", type='positive')
                                else:
                                    ui.notify(f"Failed to delete device: {response.text}", type='negative')
                        except Exception as e:
                            ui.notify(f"Error deleting device: {str(e)}", type='negative')
                        finally:
                            spinner.visible = False

                    with ui.dialog() as confirm_dialog:
                        with ui.card():
                            ui.label(f"Are you sure you want to delete {device['device_id']}?")
                            with ui.row():
                                ui.button('Cancel', on_click=confirm_dialog.close)
                                ui.button('Delete', color='red', on_click=lambda: delete_device_service())

                    ui.button('Delete', color='red', on_click=confirm_dialog.open)
                    ui.button('Restart', color='blue')

                # Device content
                with ui.column().classes('w-full space-y-8'):
                    #Device Section
                    with ui.column().classes('w-full'):
                        ui.label('DEVICE CONFIGURATION').classes('text-lg font-bold text-gray-500')
                        with ui.grid(columns=2).classes('w-full gap-4 mt-2'):
                            ui.label('Protocol:').classes('font-semibold')
                            ui.label(device['protocol_type'])
                            if device["device_ip"]:
                                ui.label('IP Address:').classes('font-semibold')
                                ui.label(device["device_ip"])
                                ui.label('Port:').classes('font-semibold')
                                ui.label(device["device_port"])

                    ui.separator()

                    #Display logs
                    with ui.column().classes('w-full'):
                        with ui.grid(columns=2).classes('w-full gap-4 mt-2'):
                            ui.label('LOGS').classes('text-lg font-bold text-gray-500')
                            get_logs_button = ui.button('Get logs',color='blue')
                        ui.label('Lastest logs from the device')
                        log_display = ui.log()

                    async def fetch_container_logs():
                        try:
                            # Show spinner
                            spinner = ui.spinner(size='2em')
                            spinner.visible = True

                            # Configure timeout
                            timeout = httpx.Timeout(300.0, connect=10.0)

                            async with httpx.AsyncClient(timeout=timeout) as client:
                                response = await client.post(
                                    f"http://{node_ip}:8000/api/add_devices/get_container_logs",
                                    params= {"device_id": device["device_id"]}
                                )
                                if response.status_code != 200:
                                    ui.notify(f"Could not connect to device (Status: {response.status_code})",
                                              type='negative',
                                              position='top')
                                    return None
                                ui.notify(f"Succesfully fetched logs from device: {device["device_id"]}")
                                data = response.json()
                                return data.get("logs", "No logs found in response")

                        except httpx.RequestError as e:
                            ui.notify(f"Connection error: {str(e)}", type='negative', position='top')
                            return None
                        except Exception as e:
                            ui.notify(f"Unexpected error: {str(e)}", type='negative', position='top')
                            return None

                        finally:
                            spinner.visible = False

                    async def update_log_display():
                        raw_logs = await fetch_container_logs()
                        if raw_logs is not None:
                            log_display.clear()
                            # Split logs by newline and push each line separately
                            for line in raw_logs.split('\n'):
                                # Remove empty lines
                                if line.strip():
                                    log_display.push(line)

                    get_logs_button.on_click(update_log_display)

                    ui.separator()

        return dialog

    # Add Service Dialog Component
    def create_add_service_dialog():
        #Variables
        selected_manufacturer = None
        selected_model = None
        selected_sensor = None

        with ui.dialog().classes('w-full max-w-4xl').props('persistent')  as dialog, ui.card().classes(
                'w-full max-h-[80vh] overflow-y-auto p-6'):
            # Header
            with ui.row().classes('w-full items-center justify-between mb-6'):
                ui.label("Add New Device Service").classes('text-2xl font-bold')
                ui.button(icon='close', on_click=dialog.close).props('flat dense')

            # Basic Information Section
            ui.label('BASIC INFORMATION').classes('text-lg font-bold text-gray-500')
            device_id = ui.input('Device ID').classes('w-full')

            service_name = ui.input('Service name').classes('w-full')

            # Device Type Selection
            device_type = ui.select(['PLC', 'Sensor'], label='Device Type').classes('w-full')

            # Content Area (Above protocol selector) - For device-specific settings
            device_content = ui.column().classes('w-full')

            # Protocol Selection
            with ui.row().classes('w-full items-center gap-4'):
                ui.label('Select Protocol:').classes('font-semibold')
                select_protocol = ui.select(['USB', 'S7Comm'], label='Protocol').classes('w-full')

            # Content Area (Below protocol selector) - For protocol-specific settings
            protocol_content = ui.column().classes('w-full space-y-6')

            def update_device_content():
                nonlocal selected_sensor, selected_model, selected_manufacturer
                device_content.clear()
                with device_content:
                    if device_type.value == 'PLC':
                        # PLC Specific Options
                        with ui.grid(columns=2).classes('w-full gap-4'):
                            selected_manufacturer = ui.select(['Siemens'], label='Manufacturer').classes('w-full')
                            selected_model = ui.select(['S7-1200'], label='Model').classes('w-full')

                        # When manufacturer changes to Siemens, set protocol to S7Comm
                        def on_manufacturer_change():
                            if selected_manufacturer.value == 'Siemens':
                                select_protocol.set_value('S7Comm')
                            protocol_update_content()

                        selected_manufacturer.on_value_change(on_manufacturer_change)

                    elif device_type.value == 'Sensor':
                        # Sensor Specific Options
                        selected_sensor = ui.select(['Microphone'], label='Sensor Type').classes('w-full')

            # Protocol-specific content templates
            def protocol_update_content():
                protocol_content.clear()
                with protocol_content:
                    if device_type.value == "Sensor" and select_protocol.value == 'USB':
                        ui.label('USB DEVICE CONFIGURATION').classes('text-lg font-bold text-gray-500')
                        with ui.grid(columns=2).classes('w-full gap-4 mt-2'):
                            ui.label('Sample rate:').classes('font-semibold')
                            mic_samplerate = ui.input(value='44100')
                            ui.label('Channels:').classes('font-semibold')
                            mic_channels = ui.input(value='1')

                        ui.label('USB DATA TRIGGER').classes('text-lg font-bold text-gray-500')
                        ui.label('Monitors when to start data sampling').classes('text-base font-bold text-gray-500')
                        with ui.grid(columns=2).classes('w-full gap-4 mt-2'):
                            ui.label('Other devices data trigger:').classes('font-semibold')
                            usb_data_trigger_source = ui.select(data_trigger_device_ids, label='Devices with data triggers').classes('w-full')
                            ui.label('Condition when to start data sampling:').classes('font-semibold')
                            usb_trigger_condition = ui.select(['True', 'False'], label='When source is == "", begin sampling').classes('w-full')

                    elif device_type.value == 'PLC' and select_protocol.value == 'S7Comm':
                        ui.label('S7COMM CONNECTION CONFIGURATION').classes('text-lg font-bold text-gray-500')
                        with ui.grid(columns=1).classes('w-full'):
                            plc_ip = ui.input(label="Device ip")
                            plc_port = ui.number(value=102, min=1, max=65535,label="Device port")
                            rack = ui.number(value=0, min=0,label="Device Rack")
                            slot = ui.number(value=1, min=0,label="Device slot")

                        # Monitoring Configuration
                        with ui.column().classes('gap-0'):  # This removes spacing between elements in the column
                            ui.label('S7COMM PROCESS MONITORING CONFIGURATION').classes('text-lg font-bold text-gray-500 mt-6')
                            ui.label('Monitors the state of the process').classes('text-base font-bold text-gray-500')
                            ui.label('Trigger type: process trigger').classes('text-base font-bold text-gray-500')
                            ui.label('!!CURRENTLY ONLY WORKS FOR MEMORYBITS!!').classes('text-base font-bold text-gray-500')

                        ui.label('Source configuration:').classes('text-base font-bold text-gray-500')
                        with ui.grid(columns=2).classes('w-full'):
                            ui.label('Source name:').classes('font-semibold')
                            process_monitoring_name = ui.input(value="Process_trigger", label="Trigger name")
                            ui.label('Data block:').classes('font-semibold')
                            process_monitoring_block = ui.number(value=+0, min=0)
                            ui.label('Byte offset:').classes('font-semibold')
                            process_monitoring_byte = ui.number(value=0, min=0)
                            ui.label('Bit offset:').classes('font-semibold')
                            process_monitoring_bit = ui.number(value=0, min=0, max=7)

                        ui.label('Condition configuration:').classes('text-base font-bold text-gray-500')
                        with ui.grid(columns=2).classes('w-full'):
                            ui.label('Condition:').classes('font-semibold')
                            process_monitoring_condition = ui.select(options=['True', 'False'],
                                                                     label='When source is == condition, begin sampling',
                                                                     value='True')

                        # Data Trigger Configuration
                        with ui.column().classes('gap-0'):  # This removes spacing between elements in the column
                            ui.label('S7COMM DATA SAMPLING TRIGGER CONFIGURATION').classes('text-lg font-bold text-gray-500 mt-6')
                            ui.label('Monitors when to start data sampling').classes('text-base font-bold text-gray-500')
                            ui.label('Trigger type: data trigger').classes('text-base font-bold text-gray-500')
                            data_trigger_checkbox = ui.checkbox(text="Include trigger")

                        #
                        data_trigger_container = ui.column().bind_visibility_from(data_trigger_checkbox, 'value')
                        with data_trigger_container:
                            ui.label('Source configuration:').classes('text-base font-bold text-gray-500')
                            with ui.grid(columns=2).classes('w-full'):
                                ui.label('Source name:').classes('font-semibold')
                                trigger_name = ui.input(value="Data_trigger", label="Trigger name")
                                ui.label('Data type:').classes('font-semibold')
                                trigger_datatype = ui.select(['Bool'], value='Bool', label="Data type")
                                ui.label('Data block:').classes('font-semibold')
                                trigger_block = ui.number(value=0, min=0, label="Data block")
                                ui.label('Byte offset:').classes('font-semibold')
                                trigger_byte = ui.number(value=0, min=0, label="Byte offset")
                                ui.label('Bit offset:').classes('font-semibold')
                                trigger_bit = ui.number(value=0, min=0, max=7, label="Bit offset")

                            ui.label('Condition configuration:').classes('text-base font-bold text-gray-500')
                            with ui.grid(columns=2).classes('w-full'):
                                ui.label('Condition:').classes('font-semibold')
                                trigger_condition = ui.select(options=['True', 'False'],
                                                                         label='When source is == condition, begin sampling',
                                                                         value='True')

                            # Data Configuration
                            ui.label('S7COMM DATA CONFIGURATION').classes('text-lg font-bold text-gray-500 mt-6')
                            with ui.grid(columns=2).classes('w-full mt-2'):
                                ui.label('Data name:').classes('font-semibold')
                                data_name = ui.input(value='ProductionData')
                                ui.label('Data block:').classes('font-semibold')
                                data_block = ui.number(value=0, min=0)

                            # Dynamic Variables Section
                            variables_container = ui.column().classes('w-full space-y-4 mt-4')
                            variables = []

                            def add_variable(name="", data_type="Real", byte_offset=0, bit_offset=0, units=""):
                                with variables_container:
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
                                                ui.button('Remove', on_click=lambda c=card: remove_variable(c)) \
                                                    .props('flat dense color=negative')

                                variables.append({
                                    'card': card,
                                    'inputs': {
                                        'name': name_input,
                                        'type': type_input,
                                        'byte_offset': byte_input,
                                        'bit_offset': bit_input,
                                        'units': units_input
                                    }
                                })

                            def remove_variable(card):
                                variables[:] = [v for v in variables if v['card'] != card]
                                card.delete()

                            # Add variable button
                            with ui.row().classes('w-full justify-end mt-4'):
                                ui.button('Add Data Variable', icon='add', on_click=add_variable).props('outline')

                        # Polling Configuration
                        ui.label('S7COMM POLLING CONFIGURATION').classes('text-lg font-bold text-gray-500 mt-6')
                        with ui.grid(columns=2).classes('w-full'):
                            ui.label('Default interval (s):').classes('font-semibold')
                            default_interval = ui.number(value=1.0, min=0.1, max=5.0, step=0.1, format='%.1f')
                            ui.label('Process monitoring interval (s):').classes('font-semibold')
                            process_interval = ui.number(value=1.0, min=0.1, max=2.0, step=0.1, format='%.1f')
                            ui.label('Data trigger interval (s):').classes('font-semibold')
                            trigger_interval = ui.number(value=1.0, min=0.1, max=2.0, step=0.1, format='%.1f')
                            ui.label('Data sampling interval (s):').classes('font-semibold')
                            data_interval = ui.number(value=1.0, min=0.1, max=2.0, step=0.1, format='%.1f')

                    else:
                        ui.label('Device and protocol does not match').classes('text-lg font-bold text-gray-500')

                    ui.separator()

                    # Modify the existing Add Service button in footer to handle saving
                    async def add_service_action():
                        try:
                            match select_protocol.value:
                                case "S7Comm":
                                    #Calculate the needed variables and build data block
                                    data_block_info = None

                                    if variables:
                                        byte_offsets = [var['inputs']['byte_offset'].value for var in variables]
                                        data_types = [var['inputs']['type'].value for var in variables]

                                        min_offset = min(byte_offsets)
                                        max_offset = max(byte_offsets)

                                        # Calculate read_size
                                        read_size = max_offset - min_offset

                                        # Add additional bytes based on data types
                                        if 'Real' in data_types or 'DWord' in data_types:
                                            read_size += 4  # Real/DWord takes 4 bytes
                                        elif 'Word' in data_types or 'Int' in data_types:
                                            read_size += 2  # Word/Int takes 2 bytes
                                        else:
                                            read_size += 1  # Default to 1 byte

                                        # Check if readsize actually is over 0
                                        if read_size <= 0:
                                            ui.notify("Please add at least one variable", type='negative')
                                            return

                                        data_block_info = {"name": data_name.value,
                                                    "db_number": data_block.value,
                                                    "read_size": read_size,
                                                    "byte_offset": min_offset,
                                                    "variables": [{"name": var['inputs']['name'].value,
                                                                   "data_type": var['inputs']['type'].value,
                                                                   "byte_offset": var['inputs']['byte_offset'].value,
                                                                   "bit_offset": var['inputs']['bit_offset'].value,
                                                                   "units": var['inputs']['units'].value} for var in variables
                                                    ]}

                                    triggers = []
                                    # building trigger and monitoring dicts:
                                    monitoring = {"trigger_type": "process_trigger",
                                                  "node_id": node_id,
                                                  "device_id": device_id.value,
                                                  "topic": f"spBv1.0/{group_id}/STATE/{node_id}/{device_id.value}",
                                                  "source": {"db_number": process_monitoring_block.value,
                                                             "name": process_monitoring_name.value,
                                                             "read_size": 1,
                                                             "data_type": "Bool",
                                                             "byte_offset": process_monitoring_byte.value,
                                                             "bit_offset": process_monitoring_bit.value,
                                                             "units": "None"},
                                                  "condition": process_monitoring_condition.value
                                    }
                                    triggers.append(monitoring)
                                    if data_trigger_checkbox.value == True:
                                        data_trigger = {"trigger_type": "data_trigger",
                                                        "node_id": node_id,
                                                        "device_id": device_id.value,
                                                        "topic": f"spBv1.0/{group_id}/STATE/{node_id}/{device_id.value}",
                                                        "source": {"db_number": trigger_block.value,
                                                                  "name": trigger_name.value,
                                                                  "read_size": 1,
                                                                  "data_type": trigger_datatype.value,
                                                                  "byte_offset": trigger_byte.value,
                                                                  "bit_offset": trigger_bit.value,
                                                                  "units": "None"},
                                                        "condition": trigger_condition.value
                                        }
                                        triggers.append(data_trigger)
                                    # Build the config using Pydantic model
                                    # noinspection PyTypeChecker
                                    config = S7CommDeviceServiceConfig(
                                        device={"group_id": group_id,
                                                "node_id": node_id,
                                                "device_id": device_id.value,
                                                "alias": service_name.value,
                                                "manufacturer": selected_manufacturer.value,
                                                "model": selected_model.value,
                                                "protocol_type": select_protocol.value,
                                                "ip": plc_ip.value,
                                                "port": plc_port.value,
                                                "rack": rack.value,
                                                "slot": slot.value
                                        },
                                        polling={
                                            "default_interval": default_interval.value,
                                            "data_interval": trigger_interval.value,
                                            "data_trigger": data_interval.value,
                                            "process_trigger": process_interval.value
                                        },
                                        triggers=triggers,
                                        data_block= data_block_info)

                                    # Convert to dict for the API
                                    config_dict = config.model_dump()

                                    device_data = {"group_id": group_id,
                                                   "node_id": node_id,
                                                   "device_id": device_id.value,
                                                   "alias": service_name.value,
                                                   "manufacturer": selected_manufacturer.value,
                                                   "model": selected_model.value,
                                                   "protocol_type": select_protocol.value,
                                                   "device_ip": plc_ip.value,
                                                   "device_port": plc_port.value}

                                case "USB":
                                    config_dict = {
                                        "device": {"group_id": group_id,
                                                "node_id": node_id,
                                                "device_id": device_id.value,
                                                "alias": service_name.value,
                                                "manufacturer": "None",
                                                "model": "None",
                                                "protocol_type": select_protocol.value,
                                                "ip": "None",
                                                "port": 0,
                                                "rack": 0,
                                                "slot": 0
                                        },
                                        "triggers": [
                                            {"trigger_type": "data_trigger",
                                            "node_id": node_id,
                                            "device_id": device_id.value,
                                            "topic": f"spBv1.0/{group_id}/STATE/{node_id}/{device_id.value}",
                                            "source": {"topic": device_to_topic.get(usb_data_trigger_source.value, ""),
                                                       "trigger_type": "data_trigger"},
                                            "condition": usb_trigger_condition.value
                                            }
                                        ],
                                        "USB_device": {
                                            "name": device_id.value,
                                            "data_type": "Audio data",
                                            "units": "Hz",
                                            "samplerate": mic_samplerate.value,
                                            "channel": mic_channels.value
                                        }
                                    }

                                    device_data = {"group_id": group_id,
                                                   "node_id": node_id,
                                                   "device_id": device_id.value,
                                                   "alias": service_name.value,
                                                   "manufacturer": "None",
                                                   "model": "None",
                                                   "protocol_type": select_protocol.value}

                            endpoint_map = {
                                "S7Comm": "add_S7_device",
                                "USB": "add_USB_microphone"
                            }
                            endpoint = endpoint_map.get(select_protocol.value)

                            # Show spinner
                            spinner = ui.spinner(size='2em')
                            spinner.visible = True

                            # Configure timeout
                            timeout = httpx.Timeout(300.0, connect=10.0)

                            async with httpx.AsyncClient(timeout=timeout) as client:
                                try:
                                    # First API call to node
                                    response_node = await client.post(
                                        f"http://{node_ip}:8000/api/add_devices/{endpoint}",
                                        json=config_dict
                                    )

                                    if response_node.status_code == 200:
                                        ui.notify("Configured the node correctly", type="positive")

                                        # Second API call to DB
                                        response_db = await client.post(
                                            f"http://localhost:8000/api/manage_nodes/add_devicedata_db",
                                            json={"device_data": device_data, "triggers": config_dict["triggers"]}
                                        )

                                        if response_db.status_code == 200:
                                            ui.notify("Service added successfully!", type='positive')
                                            dialog.close()
                                            ui.navigate.to(f"{node_id}")
                                        else:
                                            ui.notify(f"DB error: {response_db.text}", type='negative')
                                    else:
                                        ui.notify(f"Node error: {response_node.text}", type='negative')

                                except httpx.ReadTimeout:
                                    ui.notify(
                                        "Node is taking longer than expected to respond. Please check back later.",
                                        type='warning')
                                except httpx.ConnectError:
                                    ui.notify("Failed to connect to the node. Please check the node's status.",
                                              type='negative')
                                except Exception as e:
                                    ui.notify(f"Unexpected error: {str(e)}", type='negative')
                                finally:
                                    spinner.visible = False

                        except ValueError as e:
                            ui.notify(f"Validation error: {str(e)}", type='negative')
                            spinner.visible = False
                        except Exception as e:
                            ui.notify(f"Error: {str(e)}", type='negative')
                            spinner.visible = False

                    with ui.row().classes('w-full justify-end gap-4 mt-6'):
                        ui.button('Cancel', on_click=dialog.close)
                        ui.button('Add Service', on_click=add_service_action).props('color=primary')

            # Update content when protocol changes
            device_type.on_value_change(lambda: [update_device_content(), protocol_update_content()])
            select_protocol.on_value_change(protocol_update_content)

            # Initial update
            update_device_content()
            protocol_update_content()

        return dialog

    with ui.row().classes('flex-wrap gap-4'):
        # Display existing services
        for device in device_services:
            with ui.card().classes('w-64 h-32 hover:shadow-lg cursor-pointer p-2').on('click', lambda d=device: create_device_service_dialog(d).open()):
                with ui.column().classes('w-full h-full justify-between gap-0'):
                    # Header
                    with ui.row().classes('w-full items-center justify-between'):
                        ui.label(device["device_id"]).classes('text-lg font-bold')

                    # Status content
                    device_service_state = device["state"]
                    if device_service_state:
                        state_time = datetime.fromisoformat(device['last_updated'])
                        formatted_time = state_time.strftime("%Y-%m-%d %H:%M:%S")
                        match device_service_state:
                            case "True":
                                state = "Online"
                            case "False":
                                state = "Offline"
                            case _:  # If there is no state from the node in the db
                                state = f"Unknow state"

                        # Service state information
                        ui.label(f"Status: {state}").classes('text-sm')
                        ui.label(f"Time of state: {formatted_time}").classes('text-xs text-gray-500')

                    else:
                        state = "Check device connection"
                        ui.label(f"Status: {state}").classes('text-sm')

                    ui.label(f"Last checked: {time.strftime("%Y-%m-%d %H:%M:%S")}").classes('text-xs text-gray-500')

        # Add new service card (always shown)
        with ui.card().classes('w-64 h-32 hover:shadow-lg cursor-pointer').on('click', create_add_service_dialog().open):
            with ui.column().classes('w-full h-full items-center justify-center'):
                ui.icon('add', size='xl')
                ui.label("Add New Device Service").classes('text-sm')
