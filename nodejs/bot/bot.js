const zmq = require('zeromq');
const msgpack = require('msgpack5')();

class Bot {
    constructor() {
        this.logicalClock = 0;
        this.username = null;
        this.channels = [];
        
        // Socket Request-Reply
        this.reqSocket = new zmq.Request();
        
        // Socket Subscriber
        this.subSocket = new zmq.Subscriber();
        
        this.messages = [
            'Olá pessoal!',
            'Como estão?',
            'Alguém aí?',
            'Mensagem automática do bot',
            'Testando o sistema',
            'Bot em ação!',
            'Sistemas distribuídos é legal!',
            'ZeroMQ funcionando',
            'MessagePack é eficiente',
            'Relógios sincronizados!'
        ];
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
        console.log('Bot conectado ao servidor');
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
        
        if (decoded.data && decoded.data.clock) {
            this.updateClock(decoded.data.clock);
        }
        
        return decoded;
    }

    generateUsername() {
        const random = Math.floor(Math.random() * 10000);
        return `bot_${random}`;
    }

    async login() {
        this.username = this.generateUsername();
        
        const response = await this.sendRequest('login', {
            user: this.username
        });

        if (response.data.status === 'sucesso') {
            console.log(`Bot ${this.username} logado com sucesso!`);
            
            // Inscreve no tópico do próprio usuário
            this.subSocket.subscribe(this.username);
            
            return true;
        } else {
            console.log(`Erro no login: ${response.data.description}`);
            return false;
        }
    }

    async getChannels() {
        const response = await this.sendRequest('channels', {});
        this.channels = response.data.channels || [];
        
        if (this.channels.length === 0) {
            // Cria alguns canais se não existirem
            await this.sendRequest('channel', { channel: 'geral' });
            await this.sendRequest('channel', { channel: 'random' });
            await this.sendRequest('channel', { channel: 'bots' });
            
            // Atualiza lista
            const response2 = await this.sendRequest('channels', {});
            this.channels = response2.data.channels || [];
        }
        
        console.log(`Canais disponíveis: ${this.channels.join(', ')}`);
    }

    async subscribeToChannels() {
        for (const channel of this.channels) {
            this.subSocket.subscribe(channel);
            console.log(`Bot inscrito no canal: ${channel}`);
        }
    }

    getRandomChannel() {
        if (this.channels.length === 0) return null;
        const index = Math.floor(Math.random() * this.channels.length);
        return this.channels[index];
    }

    getRandomMessage() {
        const index = Math.floor(Math.random() * this.messages.length);
        return this.messages[index];
    }

    async publishRandomMessages() {
        const channel = this.getRandomChannel();
        if (!channel) return;

        console.log(`\nBot publicando 10 mensagens no canal: ${channel}`);
        
        for (let i = 0; i < 10; i++) {
            const message = this.getRandomMessage();
            
            const response = await this.sendRequest('publish', {
                user: this.username,
                channel: channel,
                message: `${message} [${i + 1}/10]`
            });

            if (response.data.status === 'OK') {
                console.log(`  ✓ Mensagem ${i + 1}/10 publicada`);
            } else {
                console.log(`  ✗ Erro na mensagem ${i + 1}/10`);
            }

            // Aguarda um pouco entre mensagens
            await this.sleep(1000);
        }
    }

    async listenMessages() {
        for await (const [topic, msg] of this.subSocket) {
            try {
                const decoded = msgpack.decode(msg);
                
                if (decoded.clock) {
                    this.updateClock(decoded.clock);
                }

                if (topic.toString() === this.username) {
                    // Mensagem privada recebida
                    console.log(`\n[BOT] Mensagem privada de ${decoded.src}: ${decoded.message}`);
                }
                // Bot não precisa logar mensagens de canais
            } catch (err) {
                // Ignora erros de parsing
            }
        }
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    async run() {
        await this.connect();
        
        let logged = false;
        while (!logged) {
            logged = await this.login();
            if (!logged) {
                await this.sleep(2000);
            }
        }

        await this.getChannels();
        await this.subscribeToChannels();

        // Inicia listener de mensagens em background
        this.listenMessages().catch(console.error);

        // Aguarda um pouco antes de começar a publicar
        await this.sleep(5000);

        // Loop infinito publicando mensagens
        while (true) {
            await this.publishRandomMessages();
            
            // Aguarda entre 10 e 30 segundos antes do próximo ciclo
            const waitTime = 10000 + Math.floor(Math.random() * 20000);
            console.log(`\nBot aguardando ${waitTime/1000}s até próximo ciclo...\n`);
            await this.sleep(waitTime);
        }
    }
}

const bot = new Bot();
bot.run().catch(console.error);