import time
from nicegui import ui
from pages.layout import create_layout
import httpx
from datetime import datetime
import pages.device_dialogs as device_dialogs

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
    device_to_topic = {}
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
                                    ui.notify(f"Failed to connect to gateway and delete device: {node_response.text}", type='negative')
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
        sensor_type = None

        with ui.dialog().classes('w-full max-w-4xl').props('persistent')  as dialog, ui.card().classes(
                'w-full max-h-[80vh] overflow-y-auto p-6'):
            # Header
            with ui.row().classes('w-full items-center justify-between mb-6'):
                ui.label("Add New Device Service").classes('text-2xl font-bold')
                ui.button(icon='close', on_click=dialog.close).props('flat dense')

            # Basic Information Section
            ui.label('BASIC INFORMATION').classes('text-lg font-bold text-gray-500')
            device_id = ui.input('Service ID').classes('w-full')

            description = ui.input('Service description').classes('w-full')

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
                nonlocal selected_sensor, selected_model, selected_manufacturer, sensor_type
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
                        sensor_type = ui.select(['Microphone'], label='Sensor Type').classes('w-full')

                        def on_sensor_change():
                            if sensor_type.value == "Microphone":
                                select_protocol.set_value('USB')
                            protocol_update_content()

                        sensor_type.on_value_change(on_sensor_change)

            # Protocol-specific content templates
            def protocol_update_content():
                protocol_content.clear()
                with protocol_content:
                    if device_type.value == "Sensor" and select_protocol.value == 'USB':
                        if sensor_type.value == "Microphone":
                            content = device_dialogs.USBMicrophoneDialog(node_id, node_ip, group_id, device_id, device_to_topic)
                            content.render_content()

                    elif device_type.value == 'PLC' and select_protocol.value == 'S7Comm':
                        content = device_dialogs.S7PlcDialog(node_id, node_ip, group_id, device_id, device_to_topic)
                        content.render_content()

                    else:
                        ui.label('Device and protocol does not match').classes('text-lg font-bold text-gray-500')

                    ui.separator()

                    with ui.row().classes('w-full justify-end gap-4 mt-6'):
                        ui.button('Cancel', on_click=dialog.close)

                        async def safe_add_service():
                            try:
                                if not content:
                                    raise ValueError("No device configuration found")

                                await device_dialogs.add_service_action(
                                    content,
                                    content.get_config(),
                                    content.get_device_data(),
                                    select_protocol,
                                    node_ip
                                )

                            except httpx.HTTPStatusError as e:
                                ui.notify(f"Server error: {e.response.text}", type='negative')
                            except ValueError as e:
                                ui.notify(f"Validation error: {str(e)}", type='warning')
                            except Exception as e:
                                ui.notify(f"Unexpected error: {str(e)}", type='negative')

                        ui.button('Add Service', on_click=safe_add_service).props('color=primary')

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
