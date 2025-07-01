from nicegui import ui

class BaseDeviceDialog:
    def __init__(self, device_type, protocol, node_id, node_ip, group_id, device_id, device_to_topic):
        self.device_type = device_type
        self.protocol = protocol
        self.node_id = node_id
        self.node_ip = node_ip
        self.group_id = group_id
        self.device_id = device_id
        self.device_to_topic = device_to_topic
        self.config = None

    def render_content(self):
        #Render the protocol-specific content
        raise NotImplementedError("Subclasses must implement this method")

    def get_config(self):
        #Return the configuration dictionary
        return self.config

    def get_device_data(self):
        #Return the basic device data dictionary
        raise NotImplementedError("Subclasses must implement this method")

    @staticmethod
    def create_endpoint_map():
        #Return the endpoint mapping for different protocols
        return {
            "S7Comm": "add_S7_device",
            "USB": "add_USB_microphone"
        }