from langchain_core.tools import tool

from db import repository
from rag.store import buscar_contexto


@tool
def buscar_manuales(consulta: str) -> str:
    """Busca en los manuales técnicos información útil para entender o resolver
    un problema. Usa una consulta corta y específica, no el ticket completo."""
    return buscar_contexto(consulta)


@tool
def tickets_similares(palabra_clave: str) -> str:
    """Busca tickets anteriores que contengan una palabra clave (por ejemplo
    'pagos' o 'login'). Sirve para ver si el problema ya ocurrió antes."""
    resultados = repository.buscar_tickets_similares(palabra_clave)
    if not resultados:
        return "No hay tickets anteriores con esa palabra."
    return str(resultados)
