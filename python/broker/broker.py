import zmq

class Broker:
    def __init__(self):
        self.context = zmq.Context()
        
        # Socket para clientes (ROUTER)
        self.client_socket = self.context.socket(zmq.ROUTER)
        self.client_socket.bind("tcp://*:5555")
        
        # Socket para servidores (DEALER)
        self.server_socket = self.context.socket(zmq.DEALER)
        self.server_socket.bind("tcp://*:5556")
        
        self.poller = zmq.Poller()
        self.poller.register(self.client_socket, zmq.POLLIN)
        self.poller.register(self.server_socket, zmq.POLLIN)
        
        self.client_count = 0
        self.server_count = 0
    
    def run(self):
        print("Broker Request-Reply iniciado")
        print("Porta clientes: 5555")
        print("Porta servidores: 5556")
        
        while True:
            socks = dict(self.poller.poll())
            
            # Mensagem do cliente para servidor
            if self.client_socket in socks:
                self.client_count += 1
                
                # Recebe todas as partes da mensagem
                frames = []
                while True:
                    frame = self.client_socket.recv()
                    frames.append(frame)
                    
                    if not self.client_socket.getsockopt(zmq.RCVMORE):
                        break
                
                # Encaminha para servidor
                for i, frame in enumerate(frames):
                    if i < len(frames) - 1:
                        self.server_socket.send(frame, zmq.SNDMORE)
                    else:
                        self.server_socket.send(frame)
                
                if self.client_count % 100 == 0:
                    print(f"Mensagens de clientes: {self.client_count}")
            
            # Mensagem do servidor para cliente
            if self.server_socket in socks:
                self.server_count += 1
                
                # Recebe todas as partes da mensagem
                frames = []
                while True:
                    frame = self.server_socket.recv()
                    frames.append(frame)
                    
                    if not self.server_socket.getsockopt(zmq.RCVMORE):
                        break
                
                # Encaminha para cliente
                for i, frame in enumerate(frames):
                    if i < len(frames) - 1:
                        self.client_socket.send(frame, zmq.SNDMORE)
                    else:
                        self.client_socket.send(frame)
                
                if self.server_count % 100 == 0:
                    print(f"Mensagens de servidores: {self.server_count}")

if __name__ == "__main__":
    broker = Broker()
    broker.run()