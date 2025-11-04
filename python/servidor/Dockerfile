FROM python:3.11-slim

WORKDIR /app

# Copiar requirements
COPY requirements.txt .

# Instalar dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fonte
COPY . .

# Criar diretório de dados
RUN mkdir -p /app/data

# Expor portas
EXPOSE 5001 5002 5003

# Comando padrão
CMD ["python", "servidor.py"]