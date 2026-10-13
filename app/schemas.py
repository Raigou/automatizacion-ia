from typing import Literal

from pydantic import BaseModel, Field

Categoria = Literal["tecnico", "facturacion", "consulta", "otro"]


class TicketIn(BaseModel):
    texto: str = Field(min_length=1, description="Texto del ticket del cliente")


class Clasificacion(BaseModel):
    urgente: bool = Field(description="True si el problema bloquea al cliente o afecta el negocio")
    categoria: Categoria = Field(description="Categoría del ticket")
    resumen: str = Field(description="Resumen del problema en una oración")
    solucion_sugerida: str | None = Field(
        default=None,
        description="Solución basada en los manuales, o null si no hay información",
    )


class TicketOut(BaseModel):
    texto_original: str
    clasificacion: Clasificacion
    guardado_en_db: bool