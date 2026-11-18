import os
import sys
import time
from pyworxcloud import WorxCloud

EMAIL = os.environ.get("WORX_EMAIL")
PASSWORD = os.environ.get("WORX_PASSWORD")
DEVICE_NAME = os.environ.get("WORX_DEVICE_NAME") # Opcional: caso tenhas mais que um robot
COMMAND = os.environ.get("MOWER_COMMAND", "status").lower()

if not EMAIL or not PASSWORD:
    print("Erro: Credenciais WORX_EMAIL e WORX_PASSWORD não definidas.")
    sys.exit(1)

def main():
    # Inicializa a ligação à nuvem Worx (tipo 'worx')
    cloud = WorxCloud(EMAIL, PASSWORD, "worx")
    
    print("A autenticar na Worx Cloud...")
    auth = cloud.authenticate()
    if not auth:
        print("Falha na autenticação. Verifica o email e a password.")
        sys.exit(1)

    cloud.connect()
    # Aguarda brevemente para garantir que o payload MQTT inicial é recebido
    time.sleep(3)

    if not cloud.devices:
        print("Nenhum dispositivo encontrado nesta conta.")
        cloud.disconnect()
        sys.exit(1)

    # Seleciona o robot pelo nome ou apanha o primeiro disponível
    mower = None
    if DEVICE_NAME and DEVICE_NAME in cloud.devices:
        mower = cloud.devices[DEVICE_NAME]
    else:
        first_key = list(cloud.devices.keys())[0]
        mower = cloud.devices[first_key]

    print(f"Conectado ao equipamento: {mower.name} (Modelo: {mower.model})")
    print(f"Estado atual: {mower.status.description} | Bateria: {mower.battery.percent}%")

    # Execução de comandos
    if COMMAND == "status":
        print("Apenas leitura de estado solicitada. Concluído.")
    elif COMMAND == "start":
        print("A enviar comando: START (Iniciar corte)...")
        cloud.start(mower.serial_number)
    elif COMMAND == "pause":
        print("A enviar comando: PAUSE (Pausar)...")
        cloud.pause(mower.serial_number)
    elif COMMAND == "home":
        print("A enviar comando: HOME (Regressar à base)...")
        cloud.home(mower.serial_number)
    else:
        print(f"Comando '{COMMAND}' desconhecido. Usa: status, start, pause ou home.")

    # Dá tempo para a mensagem MQTT ser enviada antes de fechar a ligação
    time.sleep(3)
    cloud.disconnect()
    print("Desconectado com sucesso.")

if __name__ == "__main__":
    main()
