from time import sleep
import os

container_id = os.uname()[1]

print(f"Serviço base iniciado no container: {container_id}", flush=True)

count = 0
while True:
    count += 1
    print(f"[{container_id}] Mensagem de status #{count}", flush=True)
    sleep(2)