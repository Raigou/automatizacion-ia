import logging

from fastapi import APIRouter, HTTPException, Request

from agent.builder import procesar_ticket
from app.schemas import TicketIn, TicketOut

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
def raiz():
    return {"status": "ok"}


@router.post("/procesar-ticket", response_model=TicketOut)
def procesar(ticket: TicketIn, request: Request):
    try:
        return procesar_ticket(request.app.state.agente, ticket.texto)
    except Exception:
        log.exception("Error procesando ticket")
        raise HTTPException(status_code=500, detail="Error interno procesando el ticket")