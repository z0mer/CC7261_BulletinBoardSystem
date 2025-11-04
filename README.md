# 📬 Bulletin Board System (BBS) - Sistema Distribuído

Sistema de troca de mensagens instantâneas distribuído desenvolvido como projeto da disciplina de Sistemas Distribuídos. O sistema implementa um BBS moderno utilizando arquitetura distribuída com múltiplos componentes em diferentes linguagens de programação.

## 📋 Índice

- [Sobre o Projeto](#sobre-o-projeto)
- [Arquitetura](#arquitetura)
- [Tecnologias Utilizadas](#tecnologias-utilizadas)
- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Como Executar](#como-executar)
- [Funcionalidades](#funcionalidades)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Protocolo de Comunicação](#protocolo-de-comunicação)
- [Sincronização e Replicação](#sincronização-e-replicação)

## 🎯 Sobre o Projeto

O Bulletin Board System (BBS) é um sistema distribuído que permite aos usuários:
- Trocar mensagens privadas entre si
- Criar e participar de canais públicos de discussão
- Recuperar histórico de mensagens armazenadas
- Interagir através de múltiplos servidores replicados

O sistema foi projetado seguindo princípios de sistemas distribuídos, incluindo replicação de dados, sincronização via relógio lógico de Lamport, e arquitetura baseada em mensageria com ZeroMQ.

## 🏗️ Arquitetura

O sistema é composto por 5 componentes principais:

```
┌─────────────┐
│   Cliente   │ (Node.js)
└──────┬──────┘
       │
       ├──────────────────────────────┐
       │                              │
       v                              v
┌─────────────┐              ┌─────────────┐
│   Broker    │◄────────────►│    Proxy    │ (Node.js)
│  (Req/Rep)  │              │  (Pub/Sub)  │
└──────┬──────┘              └──────┬──────┘
       │                            │
       │                            │
       v                            v
┌─────────────────────────────────────────┐
│         Servidores (Python)             │
│  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │ Server 1 │  │ Server 2 │  │Server 3│ │
│  └──────────┘  └──────────┘  └────────┘ │
│       ▲              ▲            ▲      │
│       └──────────────┴────────────┘      │
│         (Replicação entre servidores)    │
└─────────────────────────────────────────┘
              │
              v
    ┌──────────────────┐
    │   Servidor de    │ (C#)
    │   Referência     │
    └──────────────────┘
```

### Componentes

1. **Broker (Python)**: Coordena requisições síncronas usando padrão Request-Reply
2. **Proxy (Node.js)**: Gerencia publicações e assinaturas usando padrão Pub-Sub
3. **Servidores (Python)**: 3 instâncias replicadas que armazenam mensagens
4. **Cliente (Node.js)**: Interface CLI para interação do usuário
5. **Servidor de Referência (C#)**: Mantém ranking dos servidores para eleição de coordenador

## 🛠️ Tecnologias Utilizadas

### Linguagens de Programação
- **Python 3.11+**: Broker e Servidores
- **Node.js 20+**: Proxy, Cliente e Bot
- **C# (.NET 8)**: Servidor de Referência

### Bibliotecas e Frameworks
- **ZeroMQ**: Biblioteca de mensageria de alto desempenho
- **MessagePack**: Formato de serialização binária eficiente
- **Docker & Docker Compose**: Containerização e orquestração
- **Inquirer.js**: Interface CLI interativa

### Padrões de Comunicação
- **Request-Reply**: Comunicação síncrona via Broker
- **Publish-Subscribe**: Comunicação assíncrona via Proxy

## 📦 Requisitos

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **Git**

Ou, para execução local sem Docker:
- Python 3.11+
- Node.js 20+
- .NET 8 SDK

## 🚀 Instalação

### Clone o repositório

```bash
git clone <url-do-repositorio>
cd CC7261_BulletinBoardSystem
```

### Usando Docker (Recomendado)

```bash
# Construir as imagens
docker-compose build

# Iniciar todos os serviços
docker-compose up -d

# Verificar logs
docker-compose logs -f
```

### Instalação Local

#### Python (Broker e Servidores)
```bash
cd python
pip install -r requirements.txt
```

#### Node.js (Proxy, Cliente, Bot)
```bash
cd nodejs
npm install
```

#### C# (Servidor de Referência)
```bash
cd csharp/referencia
dotnet restore
```

## ▶️ Como Executar

### Método 1: Docker Compose (Recomendado)

```bash
# Iniciar toda a infraestrutura
docker-compose up -d

# Iniciar um cliente interativo
docker-compose run --rm cliente

# Parar todos os serviços
docker-compose down
```

### Método 2: Execução Manual

#### 1. Broker (Terminal 1)
```bash
cd python/broker
python broker.py
```

#### 2. Servidores de Mensagens (Terminais 2, 3, 4)

**Servidor 1:**
```bash
cd python/servidor
python servidor.py \
  --id servidor1 \
  --port 5001 \
  --peers tcp://localhost:5002,tcp://localhost:5003 \
  --referencia tcp://localhost:5558
```

**Servidor 2:**
```bash
cd python/servidor
python servidor.py \
  --id servidor2 \
  --port 5002 \
  --peers tcp://localhost:5001,tcp://localhost:5003 \
  --referencia tcp://localhost:5558
```

**Servidor 3:**
```bash
cd python/servidor
python servidor.py \
  --id servidor3 \
  --port 5003 \
  --peers tcp://localhost:5001,tcp://localhost:5002 \
  --referencia tcp://localhost:5558
```

#### 3. Broker (Terminal 5)
```bash
cd python/broker
SERVIDORES="tcp://localhost:5001,tcp://localhost:5002,tcp://localhost:5003" \
PROXY_BACKEND="tcp://localhost:5557" \
python broker.py
```

#### 4. Proxy (Terminal 6)
```bash
cd nodejs/proxy
node proxy.js
```

#### 5. Servidor de Referência (Terminal 7)
```bash
cd csharp/referencia
dotnet run
```

#### 6. Clientes (Terminais 8+)
```bash
cd nodejs/cliente
node cliente.js
```

## ✨ Funcionalidades

### Mensagens Privadas
- Enviar mensagens diretas para outros usuários
- Receber mensagens em tempo real via pub-sub
- Histórico persistente de conversas

### Canais Públicos
- Criar novos canais de discussão
- Entrar e sair de canais
- Postar mensagens em canais
- Listar canais disponíveis
- Recuperar histórico de mensagens do canal

### Persistência
- Armazenamento automático em disco (JSON)
- Recuperação de histórico de mensagens
- Replicação entre servidores

### Sincronização
- Relógio lógico de Lamport em todas as mensagens
- Sistema de ranking para eleição de coordenador
- Sincronização automática entre servidores

## 📁 Estrutura do Projeto

```
CC7261_BulletinBoardSystem/
├── python/
│   ├── broker/
│   │   └── broker.py              # Broker Request-Reply
│   └── servidor/
│       ├── servidor.py            # Servidor de mensagens
│       └── dados/                 # Armazenamento persistente
│           ├── mensagens/         # Mensagens privadas
│           └── canais/            # Mensagens de canais
├── nodejs/
│   ├── proxy/
│   │   └── proxy.js               # Proxy Pub-Sub
│   ├── cliente/
│   │   └── cliente.js             # Cliente CLI interativo
│   └── bot/
│       └── bot.js                 # Bot de teste
├── csharp/
│   └── referencia/
│       └── Program.cs             # Servidor de referência
├── docker-compose.yml             # Orquestração de containers
└── README.md
```

## 📡 Protocolo de Comunicação

### Formato de Mensagens

Todas as mensagens utilizam **MessagePack** para serialização e contêm:

```javascript
{
  "tipo": "string",           // Tipo da operação
  "origem": "string",         // ID do remetente
  "destino": "string",        // ID do destinatário/canal
  "conteudo": "string",       // Conteúdo da mensagem
  "timestamp": number,        // Relógio lógico de Lamport
  "dados": object            // Dados adicionais específicos
}
```

### Tipos de Operação

#### Request-Reply (via Broker)
- `ENVIAR_MENSAGEM`: Enviar mensagem privada
- `CRIAR_CANAL`: Criar novo canal
- `ENTRAR_CANAL`: Entrar em um canal
- `SAIR_CANAL`: Sair de um canal
- `LISTAR_CANAIS`: Listar canais disponíveis
- `HISTORICO_MENSAGENS`: Recuperar histórico privado
- `HISTORICO_CANAL`: Recuperar histórico de canal
- `PING`: Verificar status do servidor

#### Publish-Subscribe (via Proxy)
- `MENSAGEM_PRIVADA`: Notificação de nova mensagem
- `MENSAGEM_CANAL`: Notificação de mensagem em canal
- `USUARIO_ONLINE`: Usuário conectou
- `USUARIO_OFFLINE`: Usuário desconectou

## 🔄 Sincronização e Replicação

### Relógio Lógico de Lamport

Cada componente mantém seu próprio relógio lógico:

```python
# Ao enviar mensagem
self.lamport_clock += 1
mensagem['timestamp'] = self.lamport_clock

# Ao receber mensagem
self.lamport_clock = max(self.lamport_clock, mensagem['timestamp']) + 1
```

### Replicação entre Servidores

Os servidores se comunicam diretamente para replicar dados:

1. **Servidor coordenador** recebe a mensagem
2. **Propaga** para servidores secundários
3. **Aguarda confirmação** de pelo menos N-1 servidores
4. **Confirma** operação ao cliente

### Eleição de Coordenador

O servidor de referência mantém ranking baseado em:
- Número de operações bem-sucedidas
- Tempo de resposta
- Disponibilidade

## 🧪 Testes

### Executar Bot de Teste

```bash
docker-compose run --rm bot
```

O bot automaticamente:
- Conecta ao sistema
- Cria canais de teste
- Envia mensagens aleatórias
- Verifica replicação entre servidores

### Testes Manuais

1. Inicie múltiplos clientes
2. Teste mensagens privadas entre clientes
3. Crie canais e envie mensagens
4. Derrube um servidor e verifique replicação
5. Recupere histórico de mensagens