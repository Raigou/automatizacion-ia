# Automatización IA — Agente Clasificador de Tickets

Sistema de automatización empresarial que clasifica tickets de soporte usando un agente LangGraph con RAG, guarda los urgentes en PostgreSQL y orquesta el flujo con n8n.

## Tecnologías
- Python 3.11
- FastAPI
- LangGraph (agente con flujo condicional)
- LangChain + ChromaDB (RAG)
- Ollama (Llama3 + nomic-embed-text)
- PostgreSQL
- n8n
- Docker Compose

## Arquitectura

ticket llega → RAG busca contexto → LangGraph clasifica
                                          ↓
                                    ¿es urgente?
                                    sí → guarda en PostgreSQL
                                    no → devuelve clasificación

## Requisitos previos
- Ollama instalado y corriendo
- Docker Desktop corriendo
- Modelos descargados:

ollama pull llama3
ollama pull nomic-embed-text

## Cómo correr el proyecto

### 1. Clonar el repositorio

git clone https://github.com/Raigou/automatizacion-ia.git
cd automatizacion-ia

### 2. Agregar PDFs de manuales
Coloca tus archivos PDF en la carpeta data/

### 3. Levantar PostgreSQL y n8n

docker-compose up -d

### 4. Crear la tabla de tickets

docker exec -it postgres-tickets psql -U admin -d tickets -c "CREATE TABLE IF NOT EXISTS tickets (id SERIAL PRIMARY KEY, texto TEXT, categoria VARCHAR(50), resumen TEXT, solucion_sugerida TEXT, creado_en TIMESTAMP DEFAULT NOW());"

### 5. Instalar dependencias

pip install -r requirements.txt

### 6. Correr la API

uvicorn app.main:app --host 127.0.0.1 --port 8000

### 7. Probar
Abre http://127.0.0.1:8000/docs

## Ejemplo

Ticket no urgente:
{
  "texto": "Hola, tengo una consulta sobre cómo funciona GPT-4"
}

Respuesta:
{
  "texto_original": "Hola, tengo una consulta sobre cómo funciona GPT-4",
  "clasificacion": {
    "urgente": false,
    "categoria": "consulta",
    "resumen": "El cliente tiene una consulta sobre cómo funciona GPT-4",
    "solucion_sugerida": null
  },
  "guardado_en_db": false
}

Ticket urgente:
{
  "texto": "El sistema de pagos está caído, no podemos procesar ninguna transacción"
}

Respuesta:
{
  "texto_original": "El sistema de pagos está caído, no podemos procesar ninguna transacción",
  "clasificacion": {
    "urgente": true,
    "categoria": "facturacion",
    "resumen": "El sistema de pagos está caído",
    "solucion_sugerida": null
  },
  "guardado_en_db": true
}

## Características
- Agente con flujo condicional usando LangGraph
- RAG sobre documentos de soporte técnico
- Responde en español e inglés
- Tickets urgentes guardados automáticamente en PostgreSQL
- Variables de entorno con GitHub Secrets
