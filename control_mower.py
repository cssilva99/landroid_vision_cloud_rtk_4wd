import asyncio
import ast
from contextlib import redirect_stdout
import datetime
import io
import os
import re
import sys
from zoneinfo import ZoneInfo
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


# Função auxiliar para traduzir booleans ou valores comuns
def traduzir_valor(valor):
    if valor is True:
        return "Sim"
    if valor is False:
        return "Não"
    if valor is None:
        return "N/D"
    return valor


EMAIL = os.environ.get("WORX_EMAIL")
PASSWORD = os.environ.get("WORX_PASSWORD")
DEVICE_NAME = os.environ.get("WORX_DEVICE_NAME")  # Opcional: caso tenhas mais que um robot
COMMAND = os.environ.get("MOWER_COMMAND", "status").lower()

if not EMAIL or not PASSWORD:
    print("Error: Credenciais WORX_EMAIL and WORX_PASSWORD not set.")
    sys.exit(1)


def _parse_valor(raw_val: str):
    """Converte strings de representação Python (dicts, ints, bools, datetimes) com segurança."""
    raw_val = raw_val.strip()
    if raw_val == "None":
        return None
    if raw_val.startswith("<") and raw_val.endswith(">"):
        return raw_val
    try:
        return eval(
            raw_val,
            {"__builtins__": {}},
            {"datetime": datetime.datetime, "ZoneInfo": ZoneInfo},
        )
    except Exception:
        try:
            return ast.literal_eval(raw_val)
        except Exception:
            return raw_val


def resumir_robot_para_pai(texto_status: str) -> dict:
    """Extrai um resumo simples das propriedades do robot corta-relva a partir do output de debug."""
    dados = {}
    chave_atual = None
    buffer_linhas = []

    for linha in texto_status.splitlines():
        if linha.startswith("Status read-only request") or linha.startswith("==="):
            continue

        # Deteta início de uma nova propriedade no bloco DEBUG: "  nome_prop = valor"
        match = re.match(r"^  ([a-zA-Z0-9_]+) = (.*)$", linha)
        if match:
            if chave_atual is not None:
                dados[chave_atual] = _parse_valor("\n".join(buffer_linhas))
            chave_atual = match.group(1)
            buffer_linhas = [match.group(2)]
        elif chave_atual is not None:
            # Continuação de linhas multi-linha (ex.: last_status cortado ou longo)
            buffer_linhas.append(linha)

    if chave_atual is not None:
        dados[chave_atual] = _parse_valor("\n".join(buffer_linhas))

    bateria = dados.get("battery") if isinstance(dados.get("battery"), dict) else {}
    ciclos = bateria.get("cycles") if isinstance(bateria.get("cycles"), dict) else {}
    laminas = dados.get("blades") if isinstance(dados.get("blades"), dict) else {}
    erro = dados.get("error") if isinstance(dados.get("error"), dict) else {}
    firmware = dados.get("firmware") if isinstance(dados.get("firmware"), dict) else {}
    last_status = dados.get("last_status") if isinstance(dados.get("last_status"), dict) else {}

    ultima_atualizacao = last_status.get("timestamp")
    if isinstance(ultima_atualizacao, datetime.datetime):
        ultima_atualizacao_str = ultima_atualizacao.strftime("%d/%m/%Y %H:%M")
    else:
        ultima_atualizacao_str = "N/D"

    descricao_erro = erro.get("description", "Desconhecido")
    if erro.get("id") == 0 and str(descricao_erro).lower() == "no error":
        estado_erro = "Sem erros"
    else:
        estado_erro = f"{descricao_erro} (código {erro.get('id')})"

    return {
        "Bateria (%)": bateria.get("percent", "N/D"),
        "A carregar": "Sim" if bateria.get("charging") else "Não",
        "Temperatura bateria (°C)": bateria.get("temperature", "N/D"),
        "Ciclos de bateria": ciclos.get("total", "N/D"),
        "Área cortada (m²)": dados.get("area_mowed", "N/D"),
        "Tempo de lâminas (min)": laminas.get("total_on", "N/D"),
        "Estado / Erro": estado_erro,
        "Versão firmware": firmware.get("version", "N/D"),
        "Última atualização": ultima_atualizacao_str,
    }


def mostrar_resumo_pai(texto_status: str) -> None:
    resumo = resumir_robot_para_pai(texto_status)
    print("=== ESTADO DO ROBOT ===")
    for chave, valor in resumo.items():
        print(f"• {chave}: {valor}")


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

    # Selects robot by DEVICE_NAME if available, otherwise 1st available device
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

    # Imprimir propriedades mapeadas do objeto mower de forma segura
    print("=== PROPRIEDADES DIRETAS DO OBJETO MOWER ===")
    propriedades = {
        "acs_enabled": getattr(mower, "acs_enabled", None),
        "area_mowed": getattr(mower, "area_mowed", None),
        "battery": getattr(mower, "battery", None),
        "charging": mower.battery.get("charging") if isinstance(getattr(mower, "battery", None), dict) else None,
        "error": getattr(mower, "error", None),
    }

    for chave, valor in propriedades.items():
        nome_pt = TRADUCOES_PROPRIEDADES.get(chave, chave)
        print(f"  {nome_pt} = {traduzir_valor(valor)}")

    # Debug: Propriedades completas do objeto mower (também guardado para o resumo)
    debug_buffer = io.StringIO()
    print("\n=== PROPRIEDADES COMPLETAS (DEBUG) ===")
    with redirect_stdout(debug_buffer):
        for attr in dir(mower):
            if not attr.startswith("_"):
                try:
                    val = getattr(mower, attr)
                    if not callable(val):
                        print(f"  {attr} = {val}")
                except Exception:
                    pass

    debug_texto = debug_buffer.getvalue()
    print(debug_texto, end="")

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
    status_obj = getattr(mower, "status", None)
    battery_obj = getattr(mower, "battery", None)

    if isinstance(status_obj, dict):
        estado_str = status_obj.get("description", "Desconhecido")
    else:
        estado_str = getattr(status_obj, "description", "Desconhecido")

    if isinstance(battery_obj, dict):
        bateria_pct = battery_obj.get("percent", 0)
    else:
        bateria_pct = getattr(battery_obj, "percent", 0)

    # Escrever no GitHub Step Summary se executado em Actions
    summary_file = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a", encoding="utf-8") as f:
            f.write("### 🌿 Estado do Landroid Vision RTK\n\n")
            f.write(f"- **Estado:** {estado_str}\n")
            f.write(f"- **Bateria:** {bateria_pct}%\n")
            f.write(f"- **Comando Executado:** `{COMMAND}`\n")

    # Mostra o resumo simples a partir do output de debug recolhido
    print()
    mostrar_resumo_pai(debug_texto)

    await cloud.disconnect()
    print("\nSuccessfully unbound and disconnected.")


if __name__ == "__main__":
    asyncio.run(main())
