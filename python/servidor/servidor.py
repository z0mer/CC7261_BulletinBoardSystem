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
        
        self.servers = response['data']['users']
        self.update_clock(response['data']['clock'])
        return self.servers
    
    def load_data(self):
        """Carrega dados do disco"""
        try:
            users_file = self.data_dir / 'users.json'
            if users_file.exists():
                with open(users_file, 'r') as f:
                    data = json.load(f)
                    self.users = set(data.get('users', []))
            
            channels_file = self.data_dir / 'channels.json'
            if channels_file.exists():
                with open(channels_file, 'r') as f:
                    self.channels = json.load(f)
            
            messages_file = self.data_dir / 'messages.json'
            if messages_file.exists():
                with open(messages_file, 'r') as f:
                    self.messages = json.load(f)
            
            publications_file = self.data_dir / 'publications.json'
            if publications_file.exists():
                with open(publications_file, 'r') as f:
                    self.publications = json.load(f)
                    
        except Exception as e:
            print(f"Erro ao carregar dados: {e}")
    
    def save_data(self):
        """Salva dados no disco"""
        try:
            with open(self.data_dir / 'users.json', 'w') as f:
                json.dump({'users': list(self.users)}, f, indent=2)
            
            with open(self.data_dir / 'channels.json', 'w') as f:
                json.dump(self.channels, f, indent=2)
            
            with open(self.data_dir / 'messages.json', 'w') as f:
                json.dump(self.messages, f, indent=2)
            
            with open(self.data_dir / 'publications.json', 'w') as f:
                json.dump(self.publications, f, indent=2)
                
        except Exception as e:
            print(f"Erro ao salvar dados: {e}")
    
    def replicate_data(self, operation, data):
        """Replica dados para outros servidores"""
        if self.is_replicating:
            return
        
        replication_msg = {
            "operation": operation,
            "data": data,
            "source": self.server_name,
            "clock": self.increment_clock(),
            "timestamp": time.time()
        }
        
        try:
            self.pub_socket.send_multipart([
                b"replication",
                msgpack.packb(replication_msg)
            ])
        except Exception as e:
            print(f"Erro ao replicar dados: {e}")
    
    def handle_replication(self, msg):
        """Processa replicação recebida de outros servidores"""
        if msg.get('source') == self.server_name:
            return
        
        self.is_replicating = True
        
        try:
            operation = msg['operation']
            data = msg['data']
            
            self.update_clock(msg['clock'])
            
            if operation == 'login':
                self.users.add(data['user'])
            elif operation == 'channel_create':
                if data['channel'] not in self.channels:
                    self.channels[data['channel']] = {
                        'creator': data['creator'],
                        'subscribers': [],
                        'timestamp': data.get('timestamp', time.time()),
                        'clock': data.get('clock', self.logical_clock)
                    }
            elif operation == 'publish':
                self.publications.append(data)
            elif operation == 'message':
                self.messages.append(data)
            
            self.save_data()
            
        except Exception as e:
            print(f"Erro ao processar replicação: {e}")
        finally:
            self.is_replicating = False
    
    def handle_login(self, data):
        """Processa login de usuário"""
        user = data['user']
        self.update_clock(data['clock'])
        
        self.users.add(user)
        self.save_data()
        
        self.replicate_data('login', {'user': user})
        
        return {
            "success": True,
            "message": f"Usuário {user} logado",
            "clock": self.increment_clock()
        }
    
    def handle_users(self, data):
        """Retorna lista de usuários"""
        self.update_clock(data['clock'])
        
        return {
            "users": list(self.users),
            "clock": self.increment_clock()
        }
    
    def handle_channel_create(self, data):
        """Cria novo canal"""
        channel = data['channel']
        creator = data['user']
        
        self.update_clock(data['clock'])
        
        if channel in self.channels:
            return {
                "success": False,
                "message": "Canal já existe",
                "clock": self.increment_clock()
            }
        
        channel_data = {
            'creator': creator,
            'subscribers': [],
            'timestamp': time.time(),
            'clock': self.logical_clock
        }
        
        self.channels[channel] = channel_data
        self.save_data()
        
        self.replicate_data('channel_create', {
            'channel': channel,
            'creator': creator,
            'timestamp': channel_data['timestamp'],
            'clock': self.logical_clock
        })
        
        return {
            "success": True,
            "message": f"Canal {channel} criado",
            "clock": self.increment_clock()
        }
    
    def handle_channels(self, data):
        """Retorna lista de canais"""
        self.update_clock(data['clock'])
        
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
        
        return {
            "channels": channels_list,
            "clock": self.increment_clock()
        }
    
    def handle_publish(self, data):
        """Processa publicação em canal"""
        self.update_clock(data['clock'])
        
        publication = {
            'user': data['user'],
            'channel': data['channel'],
            'message': data['message'],
            'timestamp': time.time(),
            'clock': self.logical_clock
        }
        
        self.publications.append(publication)
        self.save_data()
        
        self.replicate_data('publish', publication)
        
        self.pub_socket.send_multipart([
            data['channel'].encode(),
            msgpack.packb(publication)
        ])
        
        return {
            "success": True,
            "message": "Publicação enviada",
            "clock": self.increment_clock()
        }
    
    def handle_message(self, data):
        """Processa mensagem privada"""
        self.update_clock(data['clock'])
        
        message = {
            'from': data['from'],
            'to': data['to'],
            'message': data['message'],
            'timestamp': time.time(),
            'clock': self.logical_clock
        }
        
        self.messages.append(message)
        self.save_data()
        
        self.replicate_data('message', message)
        
        self.pub_socket.send_multipart([
            f"private_{data['to']}".encode(),
            msgpack.packb(message)
        ])
        
        return {
            "success": True,
            "message": "Mensagem enviada",
            "clock": self.increment_clock()
        }
    
    def handle_history_messages(self, data):
        """Retorna histórico de mensagens privadas"""
        user = data['user']
        self.update_clock(data['clock'])
        
        user_messages = [
            msg for msg in self.messages
            if msg['from'] == user or msg['to'] == user
        ]
        
        return {
            "messages": user_messages,
            "clock": self.increment_clock()
        }
    
    def handle_history_channel(self, data):
        """Retorna histórico de canal"""
        channel = data['channel']
        self.update_clock(data['clock'])
        
        channel_publications = [
            pub for pub in self.publications
            if pub['channel'] == channel
        ]
        
        return {
            "publications": channel_publications,
            "clock": self.increment_clock()
        }
    
    def handle_sync_request(self, data):
        """Processa requisição de sincronização"""
        self.update_clock(data['clock'])
        
        return {
            "users": list(self.users),
            "channels": self.channels,
            "messages": self.messages,
            "publications": self.publications,
            "clock": self.increment_clock()
        }
    
    def heartbeat(self):
        """Envia heartbeat se for coordenador"""
        if self.rank == 1 or (self.coordinator and self.coordinator == self.server_name):
            heartbeat_msg = {
                "service": "election",
                "data": {
                    "coordinator": self.server_name,
                    "rank": self.rank,
                    "clock": self.increment_clock(),
                    "timestamp": time.time(),
                    "type": "heartbeat"
                }
            }
            
            try:
                self.pub_socket.send_multipart([
                    b"servers",
                    msgpack.packb(heartbeat_msg)
                ])
            except Exception as e:
                print(f"Erro ao enviar heartbeat: {e}")
    
    def start_election(self):
        """Inicia processo de eleição (Algoritmo de Bully)"""
        print(f"🗳️  INICIANDO ELEIÇÃO - Servidor {self.server_name} (rank {self.rank})")
        
        # No algoritmo de Bully, rank MENOR tem prioridade MAIOR
        # Se não houver servidores com rank menor disponíveis, torno-me coordenador
        self.become_coordinator()
    
    def become_coordinator(self):
        """Torna-se o novo coordenador"""
        print(f"👑 SERVIDOR {self.server_name} (RANK {self.rank}) É O NOVO COORDENADOR!")
        
        self.coordinator = self.server_name
        
        # Anunciar coordenação
        announcement = {
            "service": "election",
            "data": {
                "coordinator": self.server_name,
                "rank": self.rank,
                "clock": self.increment_clock(),
                "timestamp": time.time(),
                "type": "coordinator_announcement"
            }
        }
        
        try:
            self.pub_socket.send_multipart([
                b"servers",
                msgpack.packb(announcement)
            ])
            print(f"  ↳ Anúncio de coordenação publicado no tópico 'servers'")
        except Exception as e:
            print(f"Erro ao anunciar coordenação: {e}")
    
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
        last_coordinator_heartbeat = time.time()
        election_timeout = 15  # 15 segundos sem heartbeat = eleição
        
        # Se rank 1, já é coordenador inicial
        if self.rank == 1:
            self.coordinator = self.server_name
            print(f"👑 Servidor {self.server_name} iniciado como COORDENADOR (rank 1)")
        
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
                
                if msg.get('service') == 'election':
                    # Atualizar timestamp do último heartbeat do coordenador
                    last_coordinator_heartbeat = time.time()
                    
                    msg_data = msg.get('data', {})
                    new_coordinator = msg_data.get('coordinator')
                    
                    if new_coordinator and new_coordinator != self.coordinator:
                        print(f"✓ Novo coordenador reconhecido: {new_coordinator} (rank {msg_data.get('rank', '?')})")
                        self.coordinator = new_coordinator
                    
                    if 'clock' in msg_data:
                        self.update_clock(msg_data['clock'])
            
            # Verificar timeout do coordenador (se não for coordenador)
            if self.coordinator != self.server_name:
                time_since_last_heartbeat = time.time() - last_coordinator_heartbeat
                
                if time_since_last_heartbeat > election_timeout:
                    print(f"⚠️  Coordenador não responde há {time_since_last_heartbeat:.1f}s")
                    print(f"🗳️  Timeout detectado! Iniciando eleição...")
                    self.start_election()
                    last_coordinator_heartbeat = time.time()  # Reset após iniciar eleição
            
            # Heartbeat periódico (se for coordenador)
            if time.time() - last_heartbeat > 5:
                self.heartbeat()
                last_heartbeat = time.time()

if __name__ == "__main__":
    servidor = Servidor()
    servidor.run()