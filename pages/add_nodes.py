from nicegui import ui
from pages.layout import create_layout
import httpx
import socket
import netifaces
import os


# For use to automatically find the ip of the backend for non containerised use
async def get_ethernet_ip():
    # Return the IPv4 address of the device
    try:
        # Check all interfaces
        for interface in netifaces.interfaces():
            # Match common Ethernet interface names
            if interface.startswith(('eth', 'en', 'eno', 'ens', 'enp')):
                addrs = netifaces.ifaddresses(interface)
                # Get IPv4 addresses
                if netifaces.AF_INET in addrs:
                    for addr_info in addrs[netifaces.AF_INET]:
                        ip = addr_info['addr']
                        if not ip.startswith('127.'):  # Skip loopback
                            return ip
        raise Exception("No active Ethernet interface found")
    except Exception as e:
        print(f"Warning: {e}")
        # Fallback methods
        try:
            # Works on most Linux/Unix systems
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('10.255.255.255', 1))  # Doesn't actually send data
            print(f"Using the following ip instead {s.getsockname()[0]}")
            return s.getsockname()[0]
        except:
            print("Failed to find ethernet ip")
            return socket.gethostbyname(socket.gethostname())

@ui.page("/add_node")
def add_node_page():
    create_layout()
    ui.label('Add a new gateway').classes('text-2xl')

    # Form elements
    node_id = ui.input("Gateway ID")
    group_id = ui.input("Group ID")
    description = ui.input("Description")
    node_ip = ui.input("Gateway IP address")
    ui.label('Connections:')

    async def add_node():

        selected_services = [name for name, cb in checkboxes.items() if cb.value]
        # Add the node to the system and configure it
        node_data = {"group_id": group_id.value,
                     "node_id": node_id.value,
                     "description": description.value,
                     "ip": node_ip.value,
                     "app_services": selected_services,
                     "device_services": []
                     }

        # Show spinner
        spinner = ui.spinner(size='2em')
        spinner.visible = True

        try:
            # Configure timeout (e.g., 300 seconds = 5 minutes)
            timeout = httpx.Timeout(300.0, connect=10.0)

            async with httpx.AsyncClient(timeout=timeout) as client:
                # First try to connect to the node
                try:
                    api_url = f"http://{node_ip.value}:8000/api/configure_node/configure_node"
                    node_response = await client.post(api_url, json=node_data)

                    if node_response.status_code != 200:
                        error_detail = node_response.text if node_response.text else "No error details provided"
                        ui.notify(f"Failed to configure gateway (HTTP {node_response.status_code}): {error_detail}",
                                  type="negative")
                        return

                except httpx.ConnectError:
                    ui.notify(f"Cannot connect to gateway at: {node_ip.value}. Please check: "
                              f"1. The IP address is correct\n"
                              f"2. The gateway is powered on\n"
                              f"3. The gateway is on the same network\n",
                              type="negative", timeout=10000)
                    return
                except httpx.TimeoutException:
                    ui.notify(
                        f"Connection to node at {node_ip.value} timed out. The node might be busy or unresponsive.",
                        type="negative")
                    return
                except httpx.RequestError as e:
                    ui.notify(f"Network error while contacting node: {str(e)}", type="negative")
                    return

                # Second connect to the node for MQTT setup
                try:
                    MQTT_broker_ip = os.getenv("Backend_IP")

                    if not MQTT_broker_ip:
                        ui.notify("Backend IP is not configured in environment variables", type="negative")
                        ui.notify("Setting it to standard 192.168.0.152")
                        MQTT_broker_ip = "192.168.0.152"

                    api_url = f"http://{node_ip.value}:8000/api/configure_node/MQTT"
                    node_response = await client.post(api_url, json={"ip": MQTT_broker_ip})

                    if node_response.status_code != 200:
                        error_detail = node_response.text if node_response.text else "No error details provided"
                        ui.notify(f"Failed to configure MQTT (HTTP {node_response.status_code}): {error_detail}",
                                  type="negative")
                        return

                except Exception as e:
                    ui.notify(f"Error during MQTT configuration: {str(e)}", type="negative")
                    return

                # Third add the node to the database
                try:
                    database_response = await client.post(
                        "http://localhost:8000/api/add_nodes/create_node",
                        json=node_data
                    )

                    if database_response.status_code != 200:
                        error_detail = database_response.text if database_response.text else "No error details provided"
                        ui.notify(f"Database error (HTTP {database_response.status_code}): {error_detail}",
                                  type="negative")
                        return

                    ui.notify("Node successfully configured and added", type="positive")

                except Exception as e:
                    ui.notify(f"Database operation failed: {str(e)}", type="negative")
                    return

        except Exception as e:
            ui.notify(f"Unexpected error during node setup: {str(e)}", type="negative")
        finally:
            spinner.visible = False

    services = ['MQTT']  # Add more as needed
    checkboxes = {}

    def validate_selection():
        """Update button state and tooltip based on checkbox selections"""
        enabled = any(cb.value for cb in checkboxes.values())
        if enabled:
            add_button.enable()
            add_button.clear()
        else:
            add_button.disable()
            add_button.tooltip("Please select at least one service")
        add_button.update()  # Force UI update

    # Create checkboxes and bind change events
    for service in services:
        cb = ui.checkbox(service)
        cb.on('update:modelValue', validate_selection)
        checkboxes[service] = cb

    # Button for adding the node
    add_button = ui.button("Add gateway", on_click=add_node)
    add_button.disable()
    add_button.tooltip("Please select at least one service")

