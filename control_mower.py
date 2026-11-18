import os
import sys
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
    
    auth = await cloud.authenticate() 
    if not auth:
        print("Fails Authentication. Checks email and password.")
        sys.exit(1)

    await cloud.connect()
    # Waits to receive inicial MQTT payload (in an assynchronous way)
    await asyncio.sleep(3)

    if not cloud.devices:
        print("Zero devices in this account")
        await cloud.disconnect()
        sys.exit(1)

    # Selects robot by the 1st available name (Removido o await indevido no dicionário)
    mower = None
    if DEVICE_NAME and DEVICE_NAME in cloud.devices:
        mower = cloud.devices[DEVICE_NAME]
    else:
        first_key = list(cloud.devices.keys())[0]
        mower = cloud.devices[first_key]

    print(f"Connected to the device: {mower.name} (Model: {mower.model})")
     
    # print(f"Current Status: {mower.status.description} | Batery: {mower.battery.level}% | Batery: {mower.battery.percent}%")

    # Execute commands
    if COMMAND == "status":
        print("Status read-only request. Finished.")
    elif COMMAND == "start":
        print("Sending command: START (Begins to mow)...")
        await cloud.start(mower.serial_number)
    elif COMMAND == "pause":
        print("Sending command: PAUSE (stops)...")
        await cloud.pause(mower.serial_number)
    elif COMMAND == "home":
        print("Sending command: HOME (Returns to Dock)...")
        await cloud.home(mower.serial_number)
    else:
        print(f"Comando '{COMMAND}' desconhecido. Usa: status, start, pause ou home.")

    # The sleep() method assures that the MQTT message is sent before closing
    await asyncio.sleep(3)
    await cloud.disconnect()
    print("Successfully unbound.")
    summary_file = os.getenv("GITHUB_STEP_SUMMARY")

if summary_file:
    # Translation to portuguese is directly written to a GitHub file
    with open(summary_file, "a", encoding="utf-8") as f:
        f.write("### 🌿 Estado do Landroid Vision RTK\n\n")
        f.write(f"- **Estado:** {estado_pt}\n")
        f.write(f"- **Bateria:** {bateria_pct}%\n")
        f.write(f"- **Erro:** ")
        print(f"\n--- Ligado ao dispositivo: {mower.name} (Modelo: {mower.model}) ---")
        print(f"Número de Série: {mower.serial_number}\n")
     
        print("=== PROPRIEDADES DIRETAS DO OBJETO MOWER ===")
        for attr in dir(mower):
            if not attr.startswith("_"):
                try:
                    val = getattr(mower, attr)
                    # Ignorar métodos/funções para focar em dados e objetos
                    if not callable(val):
                        print(f"  {attr} = {val}")
                except Exception:
                    pass

        print("\n=== EXPLORAÇÃO DE SUB-OBJETOS COMUNS ===")
    
        # Verificar sub-objetos típicos (como status, battery, etc.)
        sub_objects = ["status", "battery", "schedules", "raw", "data", "capabilities"]
        for sub in sub_objects:
            if hasattr(mower, sub):
                sub_val = getattr(mower, sub)
                print(f"\n[Sub-objeto: {sub}] -> {sub_val}")
                if hasattr(sub_val, "__dict__"):
                    for sub_attr, sub_v in sub_val.__dict__.items():
                        print(f"    {sub_attr} = {sub_v}")
                elif isinstance(sub_val, dict):
                    for k, v in sub_val.items():
                        print(f"    {k}: {v}")

        await cloud.disconnect()
        print("\nDesligado com sucesso.")

if __name__ == "__main__":
    asyncio.run(main())
