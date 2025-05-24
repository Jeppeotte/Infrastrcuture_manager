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

    connections = []
    def toggle_mqtt(e):
        if e.value:  # Checkbox checked
            if 'MQTT' not in connections:
                connections.append('MQTT')
        else:  # Checkbox unchecked
            if 'MQTT' in connections:
                connections.remove('MQTT')

    ui.checkbox('MQTT', on_change=toggle_mqtt)


    async def add_node():
        # Add the node to the system and configure it
        node_data = {"group_id": group_id.value,
                     "node_id": node_id.value,
                     "description": description.value,
                     "ip": node_ip.value,
                     "app_services": connections,
                     "device_services": []
                     }

        try:
            # Show spinner
            spinner = ui.spinner(size='2em')
            spinner.visible = True

            # Configure timeout (e.g., 300 seconds = 5 minutes)
            timeout = httpx.Timeout(300.0, connect=10.0)

            async with httpx.AsyncClient(timeout=timeout) as client:
                # First connect to the node and configure it
                api_url = f"http://{node_ip.value}:8000/api/configure_node/configure_node"
                node_response = await client.post(api_url, json=node_data)

                if node_response.status_code != 200:
                    ui.notify(f"Failed to configure node, status code: {node_response.status_code}", type="negative")
                    return

                # Second connect to the node and establish connection between it and the MQTT broker
                # Get the ip of this device where the broker is hosted
                MQTT_broker_ip = os.getenv("Backend_IP")
                api_url = f"http://{node_ip.value}:8000/api/configure_node/MQTT"
                node_response = await client.post(api_url, json={"ip": MQTT_broker_ip})

                if node_response.status_code != 200:
                    ui.notify(f"Failed to start the mqtt application, status code: {node_response.status_code}", type="negative")
                    return


                # Third add the node to the database
                database_response = await client.post("http://localhost:8000/api/add_nodes/create_node",
                                                      json=node_data)

                if database_response.status_code != 200:
                    ui.notify(f"Failed to create node in db, status code: {database_response.status_code}",
                              type="negative")
                    return

                ui.notify("Node successfully configured and added")

        except Exception as e:
            ui.notify(f"Failed during node setup: {e}", type="negative")
        finally:
            spinner.visible = False

    #
    ui.button("Add gateway", on_click=add_node)