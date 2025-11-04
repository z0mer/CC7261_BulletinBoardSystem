FROM node:20-alpine

WORKDIR /app

# Copiar package.json
COPY package*.json ./

# Instalar dependências
RUN npm install

# Copiar código fonte
COPY . .

# Expor portas
EXPOSE 5556 5557

# Comando padrão
CMD ["node", "proxy.js"]