from functools import lru_cache

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

from app.config import get_settings


@lru_cache
def get_vectorstore() -> Chroma:
    s = get_settings()
    embeddings = OllamaEmbeddings(model=s.embedding_model, base_url=s.ollama_host)
    return Chroma(persist_directory=s.chroma_path, embedding_function=embeddings)


def buscar_contexto(consulta: str, k: int = 3) -> str:
    docs = get_vectorstore().similarity_search(consulta, k=k)
    return "\n\n".join(doc.page_content for doc in docs)