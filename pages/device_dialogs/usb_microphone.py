from nicegui import ui
from .base_dialog import BaseDeviceDialog
import httpx
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

class USBMicrophoneDialog(BaseDeviceDialog):
    def __init__(self, node_id, node_ip, group_id, device_id, device_to_topic):
        super().__init__("Microphone", "USB", node_id, node_ip, group_id, device_id, device_to_topic)

    def render_content(self):
        #Render USB Microphone configuration dialog
        self._render_device_config()
        self._render_data_trigger()

    def _render_device_config(self):
        node_ip = self.node_ip
        mic_data = []

        async def get_microphones():
            try:
                # Configure timeout
                timeout = httpx.Timeout(300.0, connect=10.0)

                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(
                        f"http://{node_ip}:8000/api/add_devices/available_USB_microphones"
                    )
                    if response.status_code != 200:
                        ui.notify("Failed to get microphone devices", type='negative')
                        return

                    # Update the reactive list
                    mic_data.clear()
                    mic_data.extend(response.json())
                    mic_table.refresh()

            except Exception as e:
                ui.notify(f"Unexpected error: {e}", type='negative')

        with ui.grid(columns=2).classes('w-full gap-4 mt-2'):
            ui.label('USB Microphones').classes('text-lg font-bold text-gray-500')
            ui.button('Get available microphones', on_click=get_microphones)

        self.mic_name = None
        self.mic_samplerate = None
        self.mic_channels = None


        @ui.refreshable
        def mic_table():
            if not mic_data:
                return ui.label("No microphone data available").classes('mt-4')

            def selected_mic(e):
                if e.selection:  # Check if there's a selection
                    mic = e.selection[0]
                    logger.info(f"Selected microphone: {mic}")

                    # Update the reactive variables
                    self.mic_name = mic['name']
                    self.mic_samplerate = mic['default_samplerate']
                    self.mic_channels = mic['max_input_channels']
                else:
                    # Clear all values when deselected
                    self.mic_name = None
                    self.mic_samplerate = None
                    self.mic_channels = None

            table = ui.table(
                columns=[
                    {'name': 'name', 'label': 'Name', 'field': 'name'},
                    {'name': 'samplerate', 'label': 'Samplerate', 'field': 'default_samplerate'},
                    {'name': 'channels', 'label': 'Channels', 'field': 'max_input_channels'},
                    {'name': 'in use', 'label': 'In_use', 'field': 'in_use'}
                ],
                rows=mic_data,
                row_key='name',
                on_select=lambda e: selected_mic(e),
            ).classes('w-full mt-4').set_selection('single')


            return table


        # Initial render
        mic_table()


    def _render_data_trigger(self):
        ui.label('USB DATA TRIGGER').classes('text-lg font-bold text-gray-500')
        ui.label('Monitors when to start data sampling').classes('text-base font-bold text-gray-500')
        if self.device_to_topic:
            with ui.grid(columns=2).classes('w-full gap-4 mt-2'):
                ui.label('Other devices data trigger:').classes('font-semibold')
                self.usb_data_trigger_source = ui.select(
                    list(self.device_to_topic.keys()),
                    label='Devices with data triggers'
                ).classes('w-full')
                ui.label('Condition when to start data sampling:').classes('font-semibold')
                self.usb_trigger_condition = ui.select(
                    ['True', 'False'],
                    label='When source is == "", begin sampling'
                ).classes('w-full')
        else:
            ui.label("No data triggers available on this gateway")

    def get_config(self):
        #Build and return the USB configuration dictionary
        return {
            "device": {
                "group_id": self.group_id,
                "node_id": self.node_id,
                "device_id": self.device_id.value,
                "protocol_type": self.protocol
            },
            "triggers": [
                {
                    "trigger_type": "data_trigger",
                    "node_id": self.node_id,
                    "device_id": self.device_id.value,
                    "topic": f"spBv1.0/{self.group_id}/STATE/{self.node_id}/{self.device_id.value}",
                    "source": {
                        "topic": self.device_to_topic.get(self.usb_data_trigger_source.value),
                        "trigger_type": "data_trigger"
                    },
                    "condition": self.usb_trigger_condition.value
                }
            ],
            "USB_device": {
                "name": self.mic_name,
                "data_type": "Audio data",
                "units": "Hz",
                "samplerate": self.mic_samplerate,
                "channel": self.mic_channels
            }
        }

    def get_device_data(self):
        return {
            "group_id": self.group_id,
            "node_id": self.node_id,
            "device_id": self.device_id.value,
            "protocol_type": self.protocol
        }