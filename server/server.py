import zmq
import os
from datetime import datetime

os.makedirs('/app/data', exist_ok=True)
log_file_path = '/app/data/messages.log'

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5555")

print("Servidor de mensagens iniciado e escutando na porta 5555...", flush=True)

while True:
    message = socket.recv_string()

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] Mensagem recebida: {message}\n"
    print(log_entry, end='', flush=True)

    with open(log_file_path, 'a') as f:
        f.write(log_entry)

    socket.send_string("Mensagem recebida com sucesso!")