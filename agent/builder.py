from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_ollama import ChatOllama

from agent.prompts import SYSTEM_PROMPT
from agent.tools import buscar_manuales, tickets_similares
from app.config import get_settings
from app.schemas import Clasificacion, TicketOut
from db import repository


def construir_agente():
    s = get_settings()
    llm = ChatOllama(model=s.llm_model, base_url=s.ollama_host, temperature=0)
    return create_agent(
        model=llm,
        tools=[buscar_manuales, tickets_similares],
        system_prompt=SYSTEM_PROMPT,
        response_format=ToolStrategy(Clasificacion),
    )


def clasificar_ticket(agente, texto: str, intentos: int = 3) -> Clasificacion:
    """Solo clasifica. No escribe en la base de datos.

    Si el modelo no entrega la salida estructurada, se le pide que la entregue
    continuando la misma conversación.
    """
    mensajes = [{"role": "user", "content": texto}]
    for _ in range(intentos):
        resultado = agente.invoke({"messages": mensajes})
        if "structured_response" in resultado:
            return resultado["structured_response"]
        mensajes = resultado["messages"] + [
            {"role": "user", "content": "Entrega ahora la clasificación final."}
        ]
    raise ValueError(f"El modelo no entregó una clasificación válida tras {intentos} intentos")


def procesar_ticket(agente, texto: str) -> TicketOut:
    """Clasifica y, si es urgente, guarda el ticket."""
    clasificacion = clasificar_ticket(agente, texto)

    guardado = False
    if clasificacion.urgente:
        repository.guardar_ticket(
            texto=texto,
            categoria=clasificacion.categoria,
            urgente=True,
            resumen=clasificacion.resumen,
            solucion_sugerida=clasificacion.solucion_sugerida,
        )
        guardado = True

    return TicketOut(
        texto_original=texto,
        clasificacion=clasificacion,
        guardado_en_db=guardado,
    )