FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

# Copiar csproj e restaurar dependências
COPY Referencia.csproj ./
RUN dotnet restore Referencia.csproj

# Copiar código fonte e buildar
COPY . ./
RUN dotnet publish Referencia.csproj -c Release -o /app/publish

# Imagem runtime
FROM mcr.microsoft.com/dotnet/runtime:8.0
WORKDIR /app
COPY --from=build /app/publish .

# Expor porta
EXPOSE 5559

# Rodar aplicação - ATENÇÃO: nome correto do DLL
ENTRYPOINT ["dotnet", "Referencia.dll"]