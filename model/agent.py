import os
import json
from typing import TypedDict
from langgraph.graph import StateGraph, END
from ollama import Client

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
client = Client(host=OLLAMA_HOST)

# Estado del agente — lo que viaja entre nodos del grafo
class EstadoTicket(TypedDict):
    texto: str
    contexto: str
    clasificacion: dict
    guardado_en_db: bool

# Nodo 1 — clasificar el ticket
def nodo_clasificar(estado: EstadoTicket) -> EstadoTicket:
    system_prompt = """Eres un agente clasificador de tickets de soporte técnico.
Tu tarea es analizar el ticket y responder SOLO en formato JSON con esta estructura exacta:
{
    "urgente": true o false,
    "categoria": "una de estas: tecnico, facturacion, consulta, otro",
    "resumen": "resumen breve del problema en una oración",
    "solucion_sugerida": "solución basada en el contexto provisto o null si no hay información"
}
No agregues texto fuera del JSON. No uses comillas simples. Solo JSON válido."""

    user_prompt = f"""Ticket del cliente:
{estado['texto']}

Contexto de la base de conocimiento:
{estado['contexto']}

Clasifica este ticket y sugiere una solución si el contexto lo permite."""

    respuesta = client.chat(
        model="llama3",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )

    contenido = respuesta.message.content.strip()
    contenido = contenido.replace("```json", "").replace("```", "").strip()
    clasificacion = json.loads(contenido)

    return {**estado, "clasificacion": clasificacion}

# Nodo 2 — guardar en PostgreSQL si es urgente
def nodo_guardar_db(estado: EstadoTicket) -> EstadoTicket:
    import psycopg2

    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")

    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tickets (texto, categoria, resumen, solucion_sugerida)
        VALUES (%s, %s, %s, %s)
    """, (
        estado['texto'],
        estado['clasificacion']['categoria'],
        estado['clasificacion']['resumen'],
        estado['clasificacion']['solucion_sugerida']
    ))
    conn.commit()
    cursor.close()
    conn.close()
    print("Ticket urgente guardado en PostgreSQL.")

    return {**estado, "guardado_en_db": True}

# Función que decide qué nodo sigue
def decidir_siguiente(estado: EstadoTicket) -> str:
    if estado['clasificacion'].get('urgente', False):
        return "guardar_db"
    return END

# Construir el grafo
def construir_agente():
    grafo = StateGraph(EstadoTicket)

    grafo.add_node("clasificar", nodo_clasificar)
    grafo.add_node("guardar_db", nodo_guardar_db)

    grafo.set_entry_point("clasificar")
    grafo.add_conditional_edges("clasificar", decidir_siguiente)
    grafo.add_edge("guardar_db", END)

    return grafo.compile()

agente = construir_agente()

def procesar_ticket(texto: str, contexto: str) -> dict:
    estado_inicial = {
        "texto": texto,
        "contexto": contexto,
        "clasificacion": {},
        "guardado_en_db": False
    }
    resultado = agente.invoke(estado_inicial)
    return resultado