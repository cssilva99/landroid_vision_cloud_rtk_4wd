import os
import sys
import asyncio
from pyworxcloud import WorxCloud

# Dicionário de tradução para as chaves do Landroid
TRADUCOES_PROPRIEDADES = {
    "acs_enabled": "Módulo ACS ativado",
    "api_capabilities": "Capacidades da API",
    "area_mowed": "Área cortada (m²)",
    "battery": "Bateria",
    "cycles": "Ciclos",
    "total": "Total",
    "current": "Atual",
    "reset_at": "Reposição em",
    "reset_time": "Hora de reposição",
    "temperature": "Temperatura (°C)",
    "voltage": "Voltagem (V)",
    "percent": "Percentagem (%)",
    "charging": "A carregar",
    "blade_height_min_cutoff": "Corte mín. altura da lâmina",
    "blade_height_shift": "Desvio da altura da lâmina",
    "blades": "Lâminas",
    "total_on": "Tempo total ligado (min)",
    "current_on": "Tempo atual ligado (min)",
    "capabilities": "Capacidades",
    "capabilities_available": "Capacidades disponíveis",
    "city": "Localização",
    "id": "ID",
    "country_id": "ID do país",
    "name": "Nome",
    "latitude": "Latitude",
    "longitude": "Longitude",
    "created_at": "Criado em",
    "updated_at": "Atualizado em",
    "diagnostic": "Modo de diagnóstico",
    "error": "Erro",
    "description": "Descrição",
}

# Função auxiliar para traduzir booleans ou valores comuns (opcional)
def traduzir_valor(valor):
    if valor is True:
        return "Sim"
    if valor is False:
        return "Não"
    if valor is None:
        return "N/D"
    return valor

# Exemplo de como iterar e imprimir as propriedades traduzidas
print("=== PROPRIEDADES DIRETAS DO OBJETO MOWER ===")

# Supondo que tenho um dicionário ou atributos do objeto (ex: mower.__dict__ ou similar)
# Se estiver a usar a biblioteca pyworxcloud, podes extrair as propriedades principais:
propriedades = {
    "acs_enabled": mower.acs_enabled,
    "area_mowed": mower.area_mowed,
    "battery": mower.battery,
    "charging": mower.battery.get("charging") if isinstance(mower.battery, dict) else None,
    "error": mower.error,
    # Adiciona as outras propriedades que pretendes mostrar...
}

for chave, valor in propriedades.items():
    nome_pt = TRADUCOES_PROPRIEDADES.get(chave, chave)
    print(f"  {nome_pt} = {traduzir_valor(valor)}")

EMAIL = os.environ.get("WORX_EMAIL")
PASSWORD = os.environ.get("WORX_PASSWORD")
DEVICE_NAME = os.environ.get("WORX_DEVICE_NAME")  # Opcional: caso tenhas mais que um robot
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
    # Waits to receive initial MQTT payload (in an asynchronous way)
    await asyncio.sleep(3)

    if not cloud.devices:
        print("Zero devices in this account")
        await cloud.disconnect()
        sys.exit(1)

    # Selects robot by the 1st available name
    mower = None
    if DEVICE_NAME and DEVICE_NAME in cloud.devices:
        mower = cloud.devices[DEVICE_NAME]
    else:
        first_key = list(cloud.devices.keys())[0]
        mower = cloud.devices[first_key]

    print(f"\n--- Ligado ao dispositivo: {mower.name} (Modelo: {mower.model}) ---")
    print(f"Número de Série: {mower.serial_number}\n")

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

    # Debug: Propriedades do objeto mower
    print("=== PROPRIEDADES DIRETAS DO OBJETO MOWER ===")
    for attr in dir(mower):
        if not attr.startswith("_"):
            try:
                val = getattr(mower, attr)
                if not callable(val):
                    print(f"  {attr} = {val}")
            except Exception:
                pass

    print("\n=== EXPLORAÇÃO DE SUB-OBJETOS COMUNS ===")
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
                    
    # Obter dados de forma segura para o resumo
    estado_str = getattr(getattr(mower, "status", None), "description", "Desconhecido")
    bateria_pct = getattr(getattr(mower, "battery", None), "percent", 0)

    # Escrever no GitHub Step Summary se executado em Actions
    summary_file = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a", encoding="utf-8") as f:
            f.write("### 🌿 Estado do Landroid Vision RTK\n\n")
            f.write(f"- **Estado:** {estado_str}\n")
            f.write(f"- **Bateria:** {bateria_pct}%\n")
            f.write(f"- **Comando Executado:** `{COMMAND}`\n")

    for chave, valor in propriedades.items():
     nome_pt = TRADUCOES_PROPRIEDADES.get(chave, chave)
    print(f"  {nome_pt} = {traduzir_valor(valor)}")

    await cloud.disconnect()
    print("\nSuccessfully unbound and disconnected.")

if __name__ == "__main__":
    asyncio.run(main())
