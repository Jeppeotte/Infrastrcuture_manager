from nicegui import ui

# Create the shared layout.
def create_layout():
    with ui.header(elevated=True).style('background-color: #3874c8'):
        ui.label('GATEWAY MANAGER').classes('text-white text-xl')

    with ui.left_drawer(bottom_corner=True).style('background-color: #e8f4ff'):
        with ui.row().classes('flex flex-col w-auto'):
            ui.button('Dashboard', on_click=lambda: ui.navigate.to('/')).classes('w-full')
            ui.button('Add gateway', on_click=lambda: ui.navigate.to('/add_node')).classes('w-full')
            ui.button('Manage gateways', on_click=lambda: ui.navigate.to('/manage_nodes')).classes('w-full')