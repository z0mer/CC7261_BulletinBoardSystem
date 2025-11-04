import zmq
import msgpack
import json
import time
import os
import socket
from datetime import datetime
from pathlib import Path

class Servidor:
    def __init__(self):
        self.context = zmq.Context()
        
        # Socket para Request-Reply (conecta ao broker)
        self.req_socket = self.context.socket(zmq.REP)
        self.req_socket.connect("tcp://broker:5556")
        
        # Socket para Publish (conecta ao proxy)
        self.pub_socket = self.context.socket(zmq.PUB)
        self.pub_socket.connect("tcp://proxy:5557")
        
        # Socket para receber replicações de outros servidores
        self.replication_socket = self.context.socket(zmq.SUB)
        self.replication_socket.connect("tcp://proxy:5558")
        self.replication_socket.setsockopt_string(zmq.SUBSCRIBE, "replication")
        
        # Socket para comunicação com servidor de referência
        self.ref_socket = self.context.socket(zmq.REQ)
        self.ref_socket.connect("tcp://referencia:5559")
        
        # Socket para eleição entre servidores
        self.election_socket = self.context.socket(zmq.SUB)
        self.election_socket.connect("tcp://proxy:5558")
        self.election_socket.setsockopt_string(zmq.SUBSCRIBE, "servers")
        
        # Dados
        self.users = set()
        self.channels = set()
        self.messages = []
        self.publications = []
        
        # Relógios
        self.logical_clock = 0
        self.physical_time = time.time()
        
        # Sincronização
        self.server_name = os.getenv('SERVER_NAME', socket.gethostname())
        self.rank = None
        self.coordinator = None
        self.servers = {}
        self.message_count = 0
        
        # Persistência
        self.data_dir = Path('/app/data')
        self.data_dir.mkdir(exist_ok=True)
        
        # Controle de replicação (evita loop infinito)
        self.is_replicating = False
        
        self.load_data()
        self.register_server()
        
    def increment_clock(self):
        self.logical_clock += 1
        return self.logical_clock
    
    def update_clock(self, received_clock):
        self.logical_clock = max(self.logical_clock, received_clock) + 1
        return self.logical_clock
    
    def register_server(self):
        """Registra servidor e obtém rank"""
        msg = {
            "service": "rank",
            "data": {
                "user": self.server_name,
                "timestamp": time.time(),
                "clock": self.increment_clock()
            }
        }
        
        self.ref_socket.send(msgpack.packb(msg))
        response = msgpack.unpackb(self.ref_socket.recv())
        
        self.rank = response['data']['rank']
        self.update_clock(response['data']['clock'])
        print(f"Servidor {self.server_name} registrado com rank {self.rank}")
    
    def get_servers_list(self):
        """Obtém lista de servidores"""
        msg = {
            "service": "list",
            "data": {
                "timestamp": time.time(),
                "clock": self.increment_clock()
            }
        }
        
        self.ref_socket.send(msgpack.packb(msg))
        response = msgpack.unpackb(self.ref_socket.recv())
        
        self.servers = {s['name']: s['rank'] for s in response['data']['list']}
        self.update_clock(response['data']['clock'])
    
    def heartbeat(self):
        """Envia heartbeat para servidor de referência"""
        msg = {
            "service": "heartbeat",
            "data": {
                "user": self.server_name,
                "timestamp": time.time(),
                "clock": self.increment_clock()
            }
        }
        
        try:
            self.ref_socket.send(msgpack.packb(msg))
            response = msgpack.unpackb(self.ref_socket.recv())
            self.update_clock(response['data']['clock'])
        except:
            pass
    
    def replicate_data(self, operation, data):
        """Publica operação para replicação em outros servidores"""
        if self.is_replicating:
            return  # Evita replicar uma replicação
        
        replication_msg = {
            "operation": operation,
            "data": data,
            "server": self.server_name,
            "timestamp": time.time(),
            "clock": self.increment_clock()
        }
        
        self.pub_socket.send_multipart([
            b"replication",
            msgpack.packb(replication_msg)
        ])
        
        print(f"[REPLICAÇÃO] Operação '{operation}' replicada para outros servidores")
    
    def handle_replication(self, msg):
        """Processa mensagem de replicação recebida de outro servidor"""
        try:
            # Marca que está processando replicação (evita loop)
            self.is_replicating = True
            
            operation = msg['operation']
            data = msg['data']
            source_server = msg['server']
            received_clock = msg['clock']
            
            # Ignora replicações do próprio servidor
            if source_server == self.server_name:
                self.is_replicating = False
                return
            
            self.update_clock(received_clock)
            
            # Aplica a operação localmente
            if operation == 'add_user':
                if data['user'] not in self.users:
                    self.users.add(data['user'])
                    print(f"[REPLICAÇÃO] Usuário '{data['user']}' adicionado (de {source_server})")
            
            elif operation == 'add_channel':
                if data['channel'] not in self.channels:
                    self.channels.add(data['channel'])
                    print(f"[REPLICAÇÃO] Canal '{data['channel']}' adicionado (de {source_server})")
            
            elif operation == 'add_message':
                # Verifica se mensagem já existe (evita duplicatas)
                msg_exists = any(
                    m['src'] == data['src'] and 
                    m['dst'] == data['dst'] and 
                    abs(m['timestamp'] - data['timestamp']) < 1
                    for m in self.messages
                )
                if not msg_exists:
                    self.messages.append(data)
                    print(f"[REPLICAÇÃO] Mensagem {data['src']}→{data['dst']} adicionada (de {source_server})")
            
            elif operation == 'add_publication':
                # Verifica se publicação já existe
                pub_exists = any(
                    p['channel'] == data['channel'] and 
                    p['user'] == data['user'] and 
                    abs(p['timestamp'] - data['timestamp']) < 1
                    for p in self.publications
                )
                if not pub_exists:
                    self.publications.append(data)
                    print(f"[REPLICAÇÃO] Publicação em '{data['channel']}' adicionada (de {source_server})")
            
            # Salva dados após replicação
            self.save_data()
            
        except Exception as e:
            print(f"[REPLICAÇÃO] Erro ao processar: {e}")
        finally:
            self.is_replicating = False
    
    def load_data(self):
        """Carrega dados persistidos"""
        try:
            users_file = self.data_dir / 'users.json'
            if users_file.exists():
                with open(users_file, 'r') as f:
                    self.users = set(json.load(f))
            
            channels_file = self.data_dir / 'channels.json'
            if channels_file.exists():
                with open(channels_file, 'r') as f:
                    self.channels = set(json.load(f))
            
            messages_file = self.data_dir / 'messages.json'
            if messages_file.exists():
                with open(messages_file, 'r') as f:
                    self.messages = json.load(f)
            
            publications_file = self.data_dir / 'publications.json'
            if publications_file.exists():
                with open(publications_file, 'r') as f:
                    self.publications = json.load(f)
                    
            print(f"[DADOS] Carregados: {len(self.users)} usuários, {len(self.channels)} canais, "
                  f"{len(self.messages)} mensagens, {len(self.publications)} publicações")
        except Exception as e:
            print(f"Erro ao carregar dados: {e}")
    
    def save_data(self):
        """Salva dados em disco"""
        try:
            with open(self.data_dir / 'users.json', 'w') as f:
                json.dump(list(self.users), f, indent=2)
            
            with open(self.data_dir / 'channels.json', 'w') as f:
                json.dump(list(self.channels), f, indent=2)
            
            with open(self.data_dir / 'messages.json', 'w') as f:
                json.dump(self.messages, f, indent=2)
            
            with open(self.data_dir / 'publications.json', 'w') as f:
                json.dump(self.publications, f, indent=2)
        except Exception as e:
            print(f"Erro ao salvar dados: {e}")
    
    def handle_login(self, data):
        """Processa login de usuário"""
        user = data['user']
        received_clock = data['clock']
        
        self.update_clock(received_clock)
        
        if user in self.users:
            return {
                "service": "login",
                "data": {
                    "status": "erro",
                    "timestamp": time.time(),
                    "clock": self.increment_clock(),
                    "description": "Usuário já existe"
                }
            }
        
        self.users.add(user)
        self.save_data()
        
        # Replica para outros servidores
        self.replicate_data('add_user', {'user': user})
        
        return {
            "service": "login",
            "data": {
                "status": "sucesso",
                "timestamp": time.time(),
                "clock": self.increment_clock()
            }
        }
    
    def handle_users(self, data):
        """Retorna lista de usuários"""
        self.update_clock(data['clock'])
        
        return {
            "service": "users",
            "data": {
                "timestamp": time.time(),
                "clock": self.increment_clock(),
                "users": sorted(list(self.users))
            }
        }
    
    def handle_channel_create(self, data):
        """Cria novo canal"""
        channel = data['channel']
        self.update_clock(data['clock'])
        
        if channel in self.channels:
            return {
                "service": "channel",
                "data": {
                    "status": "erro",
                    "timestamp": time.time(),
                    "clock": self.increment_clock(),
                    "description": "Canal já existe"
                }
            }
        
        self.channels.add(channel)
        self.save_data()
        
        # Replica para outros servidores
        self.replicate_data('add_channel', {'channel': channel})
        
        return {
            "service": "channel",
            "data": {
                "status": "sucesso",
                "timestamp": time.time(),
                "clock": self.increment_clock()
            }
        }
    
    def handle_channels(self, data):
        """Retorna lista de canais"""
        self.update_clock(data['clock'])
        
        return {
            "service": "channels",
            "data": {
                "timestamp": time.time(),
                "clock": self.increment_clock(),
                "channels": sorted(list(self.channels))
            }
        }
    
    def handle_publish(self, data):
        """Publica mensagem em canal"""
        channel = data['channel']
        user = data['user']
        message = data['message']
        self.update_clock(data['clock'])
        
        if channel not in self.channels:
            return {
                "service": "publish",
                "data": {
                    "status": "erro",
                    "timestamp": time.time(),
                    "clock": self.increment_clock(),
                    "message": "Canal não existe"
                }
            }
        
        # Publica no canal
        pub_msg = {
            "user": user,
            "message": message,
            "timestamp": time.time(),
            "clock": self.increment_clock()
        }
        
        self.pub_socket.send_multipart([
            channel.encode(),
            msgpack.packb(pub_msg)
        ])
        
        # Persiste publicação
        publication_data = {
            "channel": channel,
            "user": user,
            "message": message,
            "timestamp": time.time()
        }
        self.publications.append(publication_data)
        self.save_data()
        
        # Replica para outros servidores
        self.replicate_data('add_publication', publication_data)
        
        return {
            "service": "publish",
            "data": {
                "status": "OK",
                "timestamp": time.time(),
                "clock": self.logical_clock
            }
        }
    
    def handle_message(self, data):
        """Envia mensagem privada"""
        src = data['src']
        dst = data['dst']
        message = data['message']
        self.update_clock(data['clock'])
        
        if dst not in self.users:
            return {
                "service": "message",
                "data": {
                    "status": "erro",
                    "timestamp": time.time(),
                    "clock": self.increment_clock(),
                    "message": "Usuário não existe"
                }
            }
        
        # Publica no tópico do usuário destino
        msg_data = {
            "src": src,
            "message": message,
            "timestamp": time.time(),
            "clock": self.increment_clock()
        }
        
        self.pub_socket.send_multipart([
            dst.encode(),
            msgpack.packb(msg_data)
        ])
        
        # Persiste mensagem
        message_data = {
            "src": src,
            "dst": dst,
            "message": message,
            "timestamp": time.time()
        }
        self.messages.append(message_data)
        self.save_data()
        
        # Replica para outros servidores
        self.replicate_data('add_message', message_data)
        
        return {
            "service": "message",
            "data": {
                "status": "OK",
                "timestamp": time.time(),
                "clock": self.logical_clock
            }
        }
    
    def handle_history_messages(self, data):
        """Retorna histórico de mensagens privadas do usuário"""
        user = data['user']
        self.update_clock(data['clock'])
        
        user_messages = [
            msg for msg in self.messages 
            if msg['src'] == user or msg['dst'] == user
        ]
        
        # Ordena por timestamp
        user_messages.sort(key=lambda x: x['timestamp'])
        
        return {
            "service": "history_messages",
            "data": {
                "timestamp": time.time(),
                "clock": self.increment_clock(),
                "messages": user_messages
            }
        }
    
    def handle_history_channel(self, data):
        """Retorna histórico de publicações em canal"""
        channel = data['channel']
        self.update_clock(data['clock'])
        
        channel_pubs = [
            pub for pub in self.publications 
            if pub['channel'] == channel
        ]
        
        # Ordena por timestamp
        channel_pubs.sort(key=lambda x: x['timestamp'])
        
        return {
            "service": "history_channel",
            "data": {
                "timestamp": time.time(),
                "clock": self.increment_clock(),
                "publications": channel_pubs
            }
        }
    
    def handle_sync_request(self, data):
        """Responde pedido de sincronização completa de dados"""
        self.update_clock(data['clock'])
        
        return {
            "service": "sync",
            "data": {
                "timestamp": time.time(),
                "clock": self.increment_clock(),
                "users": list(self.users),
                "channels": list(self.channels),
                "messages": self.messages,
                "publications": self.publications
            }
        }
    
    def handle_list_users(self, msg):
        """Lista todos os usuários cadastrados"""
        try:
            users_list = list(self.users.keys())  # ❌ AQUI! Só retorna nomes
            
            # ✅ DEVE SER:
            users_list = [
                {
                    "username": username,
                    "timestamp": user_data.get("timestamp", 0),
                    "clock": user_data.get("clock", 0)
                }
                for username, user_data in self.users.items()
            ]
            
            response = {
                "type": "list_users_response",
                "users": users_list,
                "clock": self.logical_clock
            }
            
            self.req_socket.send(msgpack.packb(response))
        
        except Exception as e:
            print(f"❌ Erro ao listar usuários: {e}")
            error_response = {"error": str(e)}
            self.req_socket.send(msgpack.packb(error_response))
    
    def handle_list_channels(self, msg):
        """Lista todos os canais disponíveis"""
        try:
            channels_list = list(self.channels.keys())  # ❌ AQUI! Só retorna nomes
            
            # ✅ DEVE SER:
            channels_list = [
                {
                    "name": channel_name,
                    "creator": channel_data.get("creator", "unknown"),
                    "timestamp": channel_data.get("timestamp", 0),
                    "subscribers": channel_data.get("subscribers", []),
                    "clock": channel_data.get("clock", 0)
                }
                for channel_name, channel_data in self.channels.items()
            ]
            
            response = {
                "type": "list_channels_response",
                "channels": channels_list,
                "clock": self.logical_clock
            }
            
            self.req_socket.send(msgpack.packb(response))
        
        except Exception as e:
            print(f"❌ Erro ao listar canais: {e}")
            error_response = {"error": str(e)}
            self.req_socket.send(msgpack.packb(error_response))
    
    def run(self):
        """Loop principal do servidor"""
        print(f"╔{'═'*50}╗")
        print(f"║ Servidor {self.server_name:^42} ║")
        print(f"║ Rank: {self.rank:^45} ║")
        print(f"╚{'═'*50}╝")
        
        poller = zmq.Poller()
        poller.register(self.req_socket, zmq.POLLIN)
        poller.register(self.election_socket, zmq.POLLIN)
        poller.register(self.replication_socket, zmq.POLLIN)
        
        last_heartbeat = time.time()
        
        while True:
            socks = dict(poller.poll(1000))
            
            # Processa requisições
            if self.req_socket in socks:
                try:
                    msg = msgpack.unpackb(self.req_socket.recv())
                    service = msg['service']
                    data = msg['data']
                    
                    if service == 'login':
                        response = self.handle_login(data)
                    elif service == 'users':
                        response = self.handle_users(data)
                    elif service == 'channel':
                        response = self.handle_channel_create(data)
                    elif service == 'channels':
                        response = self.handle_channels(data)
                    elif service == 'publish':
                        response = self.handle_publish(data)
                    elif service == 'message':
                        response = self.handle_message(data)
                    elif service == 'history_messages':
                        response = self.handle_history_messages(data)
                    elif service == 'history_channel':
                        response = self.handle_history_channel(data)
                    elif service == 'sync':
                        response = self.handle_sync_request(data)
                    else:
                        response = {"error": "Serviço desconhecido"}
                    
                    self.req_socket.send(msgpack.packb(response))
                    self.message_count += 1
                
                except Exception as e:
                    print(f"❌ Erro ao processar requisição: {e}")
                    error_response = {"error": str(e)}
                    self.req_socket.send(msgpack.packb(error_response))
            
            # Processa mensagens de replicação
            if self.replication_socket in socks:
                try:
                    topic = self.replication_socket.recv()
                    msg = msgpack.unpackb(self.replication_socket.recv())
                    self.handle_replication(msg)
                except Exception as e:
                    print(f"❌ Erro ao processar replicação: {e}")
            
            # Processa mensagens de eleição
            if self.election_socket in socks:
                topic = self.election_socket.recv()
                msg = msgpack.unpackb(self.election_socket.recv())
                
                if msg['service'] == 'election':
                    self.coordinator = msg['data']['coordinator']
                    self.update_clock(msg['data']['clock'])
                    print(f"✓ Novo coordenador: {self.coordinator}")
            
            # Heartbeat periódico
            if time.time() - last_heartbeat > 5:
                self.heartbeat()
                last_heartbeat = time.time()

if __name__ == "__main__":
    servidor = Servidor()
    servidor.run()