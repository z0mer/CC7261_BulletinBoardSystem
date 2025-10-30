FROM node:18-alpine

WORKDIR /app

COPY package.json .
RUN npm install

COPY cliente.js .

CMD ["node", "cliente.js"]