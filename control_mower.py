import os
import sys
import time
import asyncio
from pyworxcloud import WorxCloud

EMAIL = os.environ.get("WORX_EMAIL")
PASSWORD = os.environ.get("WORX_PASSWORD")
DEVICE_NAME = os.environ.get("WORX_DEVICE_NAME") # Opcional: caso tenhas mais que um robot
COMMAND = os.environ.get("MOWER_COMMAND", "status").lower()

if not EMAIL or not PASSWORD:
    print("Error: Credenciais WORX_EMAIL and WORX_PASSWORD not set.")
    sys.exit(1)

async def main():
    # Connection to the Worx Cloud
    cloud = WorxCloud(EMAIL, PASSWORD, "worx")
    
    print("Authenticating in Worx Cloud...")
    auth = cloud.authenticate()
    if not auth:
        print("Fails Authentication. Checks email and password.")
        sys.exit(1)

    await cloud.connect()
    # Waits until the initial MQTT payload is received
    time.sleep(3)

    if not cloud.devices:
        print("Zero devices in this account")
        await cloud.disconnect()
        sys.exit(1)

    # Selects robot by the 1st available name
    mower = None
    if DEVICE_NAME and DEVICE_NAME in cloud.devices:
        mower = await cloud.devices[DEVICE_NAME]
    else:
        first_key = list(cloud.devices.keys())[0]
        mower = await cloud.devices[first_key]

    print(f"Connected to the device: {mower.name} (Model: {mower.model})")
    print(f"Current Status: {mower.status.description} | Bateria: {mower.battery.percent}%")

    # Execução de comandos
    if COMMAND == "status":
        print("Status read-only request. Finished.")
    elif COMMAND == "start":
        print("Sending command: START (Begins to mow)...")
        cloud.start(mower.serial_number)
    elif COMMAND == "pause":
        print("Sending command: PAUSE (stops)...")
        await cloud.pause(mower.serial_number)
    elif COMMAND == "home":
        print("Sending command: HOME (Returns to Dock)...")
        await cloud.home(mower.serial_number)
    else:
        print(f"Comando '{COMMAND}' desconhecido. Usa: status, start, pause ou home.")

    # Enough time for the MQTT message to be sent before closing the connection
    time.sleep(3)
    await cloud.disconnect()
    print("Successfully unbound.")

if __name__ == "__main__":
    main()
