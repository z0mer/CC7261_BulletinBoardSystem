import zmq

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://server:5555")

print("Cliente conectado ao servidor. Digite suas mensagens abaixo (ou 'sair' para encerrar).")

while True:
    message_to_send = input("> ")
    if message_to_send.lower() == 'sair':
        break
    
    if not message_to_send:
        continue

    socket.send_string(message_to_send)

    reply = socket.recv_string()
    print(f"Resposta do Servidor: {reply}")