from nicegui import ui
from pages.layout import create_layout
import httpx
import datetime

@ui.page("/manage_nodes")
async def manage_nodes():
    create_layout()
    ui.label('Manage a one of the existing gateways').classes('text-2xl')

    async def get_nodes_data():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8000/api/manage_nodes/get_all_nodes")
                data = response.json()
                return data
        except Exception as e:
            ui.notify(f"Failed to load the nodes: {e}", type="negative")

    async def get_nodes_status():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8000/api/manage_nodes/get_node_state")
                data = response.json()
                return data
        except Exception as e:
            ui.notify(f"Failed to load the state of the nodes: {e}", type="negative")

    def open_node_manager(node_id):
        ui.navigate.to(f"/manage_nodes/{node_id}")

    node_data = await get_nodes_data()
    # Fetch all the latest states from the different edge_nodes
    nodes_status = await get_nodes_status()

    with ui.row().classes("w-full"):
        with ui.column().classes("w-full grid grid-cols-3 gap-4"):
            for node in node_data:
                with ui.card().on("click", lambda _, n=node: open_node_manager(n["node_id"])) \
                        .classes("cursor-pointer hover:bg-blue-50 p-4"):
                    ui.label(f"{node['node_id']}").classes("text-lg font-bold")
                    ui.label(f"Group: {node['group_id']}")
                    ui.label(f"IP: {node['ip']}")
                    #Check if the node_id is within the node_state
                    node_status = nodes_status.get(node["node_id"])
                    if node_status:
                        node_state = node_status.get("state")
                        state_time = datetime.datetime.fromtimestamp(node_status.get("time"))
                        ui.label(f'Time of state: {state_time.strftime("%Y-%m-%d %H:%M:%S")}')
                        match node_state:
                            case "True":
                                state = "Online"
                            case "False":
                                state = "Offline"
                            case _:  # If there is no 'state' key or it's something unexpected
                                state = f"Unknown node state: {node_state}"
                    else:
                        state = "Node not connected to the backend"
                    ui.label(f'State: {state}')



