import socket
import netifaces

def get_ethernet_ip():
    """Returns the IPv4 address of the primary Ethernet interface"""
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
            return s.getsockname()[0]
        except:
            print("Failed to find ethernet ip")
            return socket.gethostbyname(socket.gethostname())

if __name__ == '__main__':
    # Get the broker IP
    broker_ip = get_ethernet_ip()
    print(f"MQTT broker is running at: {broker_ip}")