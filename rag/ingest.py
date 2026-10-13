import logging
from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def indexar() -> None:
    s = get_settings()

    paginas = []
    for pdf in sorted(Path(s.data_path).glob("*.pdf")):
        paginas.extend(PyPDFLoader(str(pdf)).load())
    log.info("%d páginas cargadas", len(paginas))

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = splitter.split_documents(paginas)
    log.info("%d chunks creados", len(chunks))

    embeddings = OllamaEmbeddings(model=s.embedding_model, base_url=s.ollama_host)
    Chroma.from_documents(
        chunks,
        embeddings,
        persist_directory=s.chroma_path,
    )
    log.info("Índice guardado en %s", s.chroma_path)


if __name__ == "__main__":
    indexar()