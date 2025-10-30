const zmq = require('zeromq');

class Proxy {
    constructor() {
        this.pubCount = 0;
        this.subCount = 0;
    }

    async run() {
        // Socket XSUB - recebe de publishers
        const xsub = new zmq.XSubscriber();
        await xsub.bind('tcp://*:5557');
        
        // Socket XPUB - envia para subscribers
        const xpub = new zmq.XPublisher();
        await xpub.bind('tcp://*:5558');
        
        console.log('Proxy Pub-Sub iniciado');
        console.log('Porta publishers (XSUB): 5557');
        console.log('Porta subscribers (XPUB): 5558');
        
        // Proxy assíncrono
        this.proxyMessages(xsub, xpub);
    }

    async proxyMessages(xsub, xpub) {
        // Encaminha mensagens de subscribers para publishers (inscrições)
        (async () => {
            for await (const [msg] of xpub) {
                this.subCount++;
                if (this.subCount % 10 === 0) {
                    console.log(`Inscrições: ${this.subCount}`);
                }
                await xsub.send(msg);
            }
        })();

        // Encaminha mensagens de publishers para subscribers
        (async () => {
            for await (const frames of xsub) {
                this.pubCount++;
                if (this.pubCount % 100 === 0) {
                    console.log(`Publicações: ${this.pubCount}`);
                }
                await xpub.send(frames);
            }
        })();
    }
}

const proxy = new Proxy();
proxy.run().catch(console.error);