"""
    Lubo: mods to exisitng port status app
    
    client_status

    Application Purpose
    ===================
    This application will set the device description to show a binary
    representation of WAN, LAN, WiFi, and IP Verify status.  It will also
    send an alert if there are no clients connected to either LAN or WiFi.

    1 represents connected/up/pass, 0 represents disconnected/down/fail.

    Description is updated every hour (3600 sec), but only synced to NCM
    if there is a change from the current description.

    Alerts are sent via a custom event: "no_clients_connected".
    Alerts are cleared via custom event: "clients_connected"
"""

import time
from csclient import EventingCSClient

APP_NAME = 'client_status'
DEBUG = False
MODELS_WITHOUT_WAN = ['CBA', 'W18', 'W200', 'W400', 'L950', 'IBR200', '4250']

# NCOS Configuration Paths
WAN_DEVICES_PATH = '/status/wan/devices'
ETHERNET_STATUS_PATH = '/status/ethernet'
PRODUCT_INFO_PATH = '/status/product_info/product_name'
SYSTEM_DESC_PATH = 'config/system/desc'
WIFI_RADIO_STATUS_PATH = '/status/wlan/radio' #Added for WIFI clients
WIFI_CLIENTS_STATUS_PATH = '/status/wlan/clients' #Added for WIFI clients
IPVERIFY_STATUS_PATH = '/status/ipverify'  # Added for IP Verify

# Alert Event Name for no attached clients to LAN/WIFI
ALERT_EVENT_NAME = 'no_clients_connected'
ALERT_CLEAR_EVENT_NAME = 'clients_connected'

cp = EventingCSClient('client_status') # Update client ID

if DEBUG:
    cp.log("DEBUG ENABLED")
    cp.log("Getting Model")

model = cp.get(PRODUCT_INFO_PATH)
if DEBUG:
    cp.log(model)

def get_wan_status(wans, model):
    """Gets the status of Ethernet WAN connections (1 for connected, 0 for not)."""
    if not wans:
        return 0 if any(x in model for x in MODELS_WITHOUT_WAN) else 0

    for wan in (wan for wan in wans if 'ethernet' in wan):
        summary = cp.get(f'{WAN_DEVICES_PATH}/{wan}/status/summary')
        if summary and 'connected' in summary:
            return 1
        elif summary and ('available' in summary or 'standby' in summary):
            return 1
    return 0

def get_lan_status(ports, model):
    """Gets the status of Ethernet LAN ports (1 if any port is up, 0 otherwise)."""
    if not ports:
        return 0
    for port in ports:
        if (port['port'] == 0 and any(x in model for x in MODELS_WITHOUT_WAN)) or (port['port'] >= 1):
            if port['link'] == "up":
                return 1
    return 0

def get_wifi_status():
    """Gets the status of Wi-Fi clients (1 if connected, 0 otherwise)."""
    try:
        radios = cp.get(WIFI_RADIO_STATUS_PATH)
        if radios:
            for radio in radios:
                if radio.get('enabled', False):
                    clients = cp.get(f"{WIFI_CLIENTS_STATUS_PATH}?radio={radio['id']}")
                    if clients:
                        return 1
        return 0
    except Exception as e:
        cp.log(f"Error getting Wi-Fi status: {e}")
        return 0

def get_ipverify_status():
    """Gets the overall status of IP Verify (1 if all pass, 0 if any fail)."""
    try:
        ipverifys = cp.get(IPVERIFY_STATUS_PATH)
        if not ipverifys:  # No IP Verify configured
            return 0
        for ipverify in ipverifys:
            testpass = cp.get(f'{IPVERIFY_STATUS_PATH}/{ipverify}/pass')
            if not testpass:  # If any test fails, return 0
                return 0
        return 1  # All tests passed
    except Exception as e:
        cp.log(f"Error getting IP Verify status: {e}")
        return 0 # Return 0 on error


def send_alert(message):
    """Sends a custom alert event."""
    cp.raise_event(ALERT_EVENT_NAME, message)
    cp.log(f"Alert sent: {message}")

def clear_alert():
    """Sends custom event to clear the alert"""
    cp.raise_event(ALERT_CLEAR_EVENT_NAME, "Clients reconnected")
    cp.log("Alert cleared")

# Keep track of whether an alert has been sent
alert_sent = False

while True:
    try:
        wans = cp.get(WAN_DEVICES_PATH)
        ports = cp.get(ETHERNET_STATUS_PATH)

        wan_status = get_wan_status(wans, model)
        lan_status = get_lan_status(ports, model)
        wifi_status = get_wifi_status()
        ipverify_status = get_ipverify_status()  # Get IP Verify status

        # Check for no clients condition
        if lan_status == 0 and wifi_status == 0:
            if not alert_sent:
                send_alert("No clients connected to LAN or Wi-Fi.")
                alert_sent = True
        elif alert_sent:
            clear_alert()
            alert_sent = False

        # Create the binary status string, including IP Verify
        #client_status = f"WAN:{wan_status} LAN:{lan_status} WIFI:{wifi_status} IPV:{ipverify_status}"
        client_status = f"{wan_status}{ipverify_status}{lan_status}{wifi_status}"

        # Only update if the description has changed
        current_description = cp.get(SYSTEM_DESC_PATH)
        if client_status != current_description:
            if DEBUG:
                cp.log("WRITING DESCRIPTION")
                cp.log(client_status)
            cp.put(SYSTEM_DESC_PATH, client_status)

    except Exception as err:
        cp.log("Failed with exception={} err={}".format(type(err), str(err)))

    time.sleep(3600)
