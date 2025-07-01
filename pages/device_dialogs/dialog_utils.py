import httpx
from nicegui import ui
from models.manage_nodes import DeviceDataSchema, AddDeviceSchema
from pydantic import ValidationError

async def add_service_action(dialog, config_dict, device_data, select_protocol, node_ip):
    # Common function to handle the add service action
    endpoint_map = {
        "S7Comm": "add_S7_device",
        "USB": "add_USB_microphone"
    }
    endpoint = endpoint_map.get(select_protocol.value)

    spinner = ui.spinner(size='2em')
    spinner.visible = True

    timeout = httpx.Timeout(300.0, connect=10.0)

    try:
        # Validate the data
        try:
            # Validate device_data against DeviceDataSchema
            validated_device = DeviceDataSchema(**device_data)

            # Validate full config against AddDeviceSchema
            validated_config = AddDeviceSchema(
                device_data=validated_device,
                triggers=config_dict.get("triggers", [])
            )
        except ValidationError as e:
            # Format Pydantic validation errors nicely
            errors = []
            for error in e.errors():
                field = "→".join(str(loc) for loc in error['loc'])
                msg = error['msg']
                errors.append(f"{field}: {msg}")
            ui.notify("Validation errors:\n" + "\n".join(errors), type='negative')
            return

        async with httpx.AsyncClient(timeout=timeout) as client:
            # API call to gateway
            response_node = await client.post(
                f"http://{node_ip}:8000/api/add_devices/{endpoint}",
                json=config_dict
            )

            if response_node.status_code == 200:
                # API call to DB
                response_db = await client.post(
                    "http://localhost:8000/api/manage_nodes/add_devicedata_db",
                    json={"device_data": device_data, "triggers": config_dict["triggers"]}
                )

                if response_db.status_code == 200:
                    ui.notify("Service added successfully!", type='positive')
                    ui.navigate.to(f"{device_data['node_id']}")
                else:
                    ui.notify(f"DB error: {response_db.text}", type='negative')
            else:
                # Custom friendly message for Docker container name conflict
                error_text = response_node.text
                if "Conflict. The container name" in error_text and "already in use" in error_text:
                    ui.notify("A device service with this ID already exists. Please change the 'Device ID'.",
                              type='negative')
                else:
                    ui.notify(f"Gateway error: {error_text}", type='negative')

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