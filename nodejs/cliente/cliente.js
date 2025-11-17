const zmq = require('zeromq');
const msgpack = require('msgpack5')();
const readline = require('readline');

class Cliente {
    constructor() {
        this.logicalClock = 0;
        this.username = null;
        
        // Socket Request-Reply
        this.reqSocket = new zmq.Request();
        
        // Socket Subscriber
        this.subSocket = new zmq.Subscriber();
        
        this.rl = readline.createInterface({
            input: process.stdin,
            output: process.stdout
        });
    }

    incrementClock() {
        this.logicalClock++;
        return this.logicalClock;
    }

    updateClock(receivedClock) {
        this.logicalClock = Math.max(this.logicalClock, receivedClock) + 1;
        return this.logicalClock;
    }

    async connect() {
        await this.reqSocket.connect('tcp://broker:5555');
        await this.subSocket.connect('tcp://proxy:5558');
        console.log('Conectado ao servidor');
    }

    async sendRequest(service, data) {
        const msg = {
            service: service,
            data: {
                ...data,
                timestamp: Date.now() / 1000,
                clock: this.incrementClock()
            }
        };

        await this.reqSocket.send(msgpack.encode(msg));
        const [response] = await this.reqSocket.receive();
        const decoded = msgpack.decode(response);
        
        if (decoded.clock) {
            this.updateClock(decoded.clock);
        }
        
        return decoded;
    }

    async login() {
        return new Promise((resolve) => {
            this.rl.question('Digite seu nome de usuário: ', async (username) => {
                this.username = username;
                
                const response = await this.sendRequest('login', {
                    user: username
                });

                if (response.success) {
                    console.log('Login realizado com sucesso!');
                    
                    // Inscreve no tópico do próprio usuário para mensagens privadas
                    this.subSocket.subscribe(username);
                    
                    resolve(true);
                } else {
                    console.log(`Erro no login: ${response.message || 'Erro desconhecido'}`);
                    resolve(false);
                }
            });
        });
    }

    async listUsers() {
        const response = await this.sendRequest('users', {});
        console.log('\n=== Usuários cadastrados ===');
        if (response.users) {
            response.users.forEach(user => console.log(`  - ${user}`));
        }
        console.log('');
    }

    async createChannel() {
        return new Promise((resolve) => {
            this.rl.question('Nome do canal: ', async (channel) => {
                const response = await this.sendRequest('channel', {
                    channel: channel,
                    user: this.username
                });

                if (response.success) {
                    console.log('Canal criado com sucesso!');
                } else {
                    console.log(`Erro: ${response.message || 'Erro ao criar canal'}`);
                }
                resolve();
            });
        });
    }

    async listChannels() {
        const response = await this.sendRequest('channels', {});
        console.log('\n=== Canais disponíveis ===');
        if (response.channels) {
            response.channels.forEach(channel => {
                const name = typeof channel === 'string' ? channel : channel.name;
                console.log(`  - ${name}`);
            });
        }
        console.log('');
    }

    async subscribeChannel() {
        return new Promise((resolve) => {
            this.rl.question('Nome do canal para se inscrever: ', async (channel) => {
                this.subSocket.subscribe(channel);
                console.log(`Inscrito no canal: ${channel}`);
                resolve();
            });
        });
    }

    async publishMessage() {
        return new Promise((resolve) => {
            this.rl.question('Canal: ', (channel) => {
                this.rl.question('Mensagem: ', async (message) => {
                    const response = await this.sendRequest('publish', {
                        user: this.username,
                        channel: channel,
                        message: message
                    });

                    if (response.success) {
                        console.log('Mensagem publicada!');
                    } else {
                        console.log(`Erro: ${response.message || 'Erro ao publicar'}`);
                    }
                    resolve();
                });
            });
        });
    }

    async sendPrivateMessage() {
        return new Promise((resolve) => {
            this.rl.question('Usuário destino: ', (dst) => {
                this.rl.question('Mensagem: ', async (message) => {
                    const response = await this.sendRequest('message', {
                        from: this.username,
                        to: dst,
                        message: message
                    });

                    if (response.success) {
                        console.log('Mensagem enviada!');
                    } else {
                        console.log(`Erro: ${response.message || 'Erro ao enviar'}`);
                    }
                    resolve();
                });
            });
        });
    }

    async viewMessageHistory() {
        const response = await this.sendRequest('history_messages', {
            user: this.username
        });
        
        console.log('\n=== Histórico de Mensagens Privadas ===');
        if (!response.messages || response.messages.length === 0) {
            console.log('  Nenhuma mensagem encontrada.');
        } else {
            response.messages.forEach(msg => {
                const date = new Date(msg.timestamp * 1000).toLocaleString();
                if (msg.from === this.username) {
                    console.log(`  [${date}] → Para ${msg.to}: ${msg.message}`);
                } else {
                    console.log(`  [${date}] ← De ${msg.from}: ${msg.message}`);
                }
            });
        }
        console.log('');
    }

    async viewChannelHistory() {
        return new Promise((resolve) => {
            this.rl.question('Nome do canal: ', async (channel) => {
                const response = await this.sendRequest('history_channel', {
                    channel: channel
                });
                
                console.log(`\n=== Histórico do Canal: ${channel} ===`);
                if (!response.publications || response.publications.length === 0) {
                    console.log('  Nenhuma publicação encontrada.');
                } else {
                    response.publications.forEach(pub => {
                        const date = new Date(pub.timestamp * 1000).toLocaleString();
                        console.log(`  [${date}] ${pub.user}: ${pub.message}`);
                    });
                }
                console.log('');
                resolve();
            });
        });
    }

    async listenMessages() {
        for await (const [topic, msg] of this.subSocket) {
            try {
                const decoded = msgpack.decode(msg);
                
                if (decoded.clock) {
                    this.updateClock(decoded.clock);
                }

                if (topic.toString() === this.username || topic.toString().startsWith('private_')) {
                    // Mensagem privada
                    console.log(`\n[MENSAGEM PRIVADA de ${decoded.from}]: ${decoded.message}`);
                } else {
                    // Mensagem de canal
                    console.log(`\n[${topic.toString()}] ${decoded.user}: ${decoded.message}`);
                }
            } catch (err) {
                console.error('Erro ao processar mensagem:', err);
            }
        }
    }

    showMenu() {
        console.log('\n=== Menu ===');
        console.log('1. Listar usuários');
        console.log('2. Criar canal');
        console.log('3. Listar canais');
        console.log('4. Inscrever em canal');
        console.log('5. Publicar mensagem em canal');
        console.log('6. Enviar mensagem privada');
        console.log('7. Ver histórico de mensagens privadas');
        console.log('8. Ver histórico de canal');
        console.log('9. Sair');
        console.log('');
    }

    async menu() {
        return new Promise((resolve) => {
            this.showMenu();
            this.rl.question('Escolha uma opção: ', async (option) => {
                switch(option) {
                    case '1':
                        await this.listUsers();
                        break;
                    case '2':
                        await this.createChannel();
                        break;
                    case '3':
                        await this.listChannels();
                        break;
                    case '4':
                        await this.subscribeChannel();
                        break;
                    case '5':
                        await this.publishMessage();
                        break;
                    case '6':
                        await this.sendPrivateMessage();
                        break;
                    case '7':
                        await this.viewMessageHistory();
                        break;
                    case '8':
                        await this.viewChannelHistory();
                        break;
                    case '9':
                        console.log('Saindo...');
                        process.exit(0);
                        break;
                    default:
                        console.log('Opção inválida');
                }
                resolve();
            });
        });
    }

    async run() {
        await this.connect();
        
        let logged = false;
        while (!logged) {
            logged = await this.login();
        }

        // Inicia listener de mensagens em background
        this.listenMessages().catch(console.error);

        // Loop do menu
        while (true) {
            await this.menu();
        }
    }
}

const cliente = new Cliente();
cliente.run().catch(console.error);