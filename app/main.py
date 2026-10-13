import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from agent.builder import construir_agente
from app.routes import router

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.agente = construir_agente()
    yield


app = FastAPI(title="Automatización IA API", lifespan=lifespan)
app.include_router(router)