FROM node:18-slim

# Instalar timezone
RUN apt-get update && apt-get install -y tzdata && rm -rf /var/lib/apt/lists/*

# Configurar timezone
ENV TZ=America/Sao_Paulo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

# Copiar package.json
COPY package*.json ./

# Instalar dependências
RUN npm install

# Copiar código fonte
COPY . .

# Comando padrão
CMD ["node", "bot.js"]