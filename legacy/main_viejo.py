import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from model.rag import cargar_documentos, crear_vectorstore, buscar_contexto
from model.agent import procesar_ticket

APP_ENV = os.getenv("APP_ENV", "development")

app = FastAPI(title="Automatizacion IA API")

# Inicializar RAG al arrancar
print("Inicializando RAG...")
documentos = cargar_documentos()
vectorstore = crear_vectorstore(documentos)
print("RAG listo.")

# User prompt — el ticket del cliente
class Ticket(BaseModel):
    texto: str

@app.get("/")
def root():
    return {
        "status": "ok",
        "descripcion": "Agente clasificador de tickets con RAG y LangGraph",
        "environment": APP_ENV
    }

@app.post("/procesar-ticket")
def procesar(ticket: Ticket):
    try:
        # RAG — buscar contexto relevante
        contexto = buscar_contexto(ticket.texto, vectorstore)

        # Agente LangGraph — clasificar y guardar si es urgente
        resultado = procesar_ticket(ticket.texto, contexto)

        return {
            "texto_original": ticket.texto,
            "clasificacion": resultado['clasificacion'],
            "guardado_en_db": resultado['guardado_en_db']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
