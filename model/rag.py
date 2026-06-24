import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Chroma

DATA_PATH = "data/"
CHROMA_PATH = "chroma_db/"

def cargar_documentos():
    documentos = []
    for archivo in os.listdir(DATA_PATH):
        if archivo.endswith(".pdf"):
            loader = PyPDFLoader(DATA_PATH + archivo)
            documentos.extend(loader.load())
    print(f"{len(documentos)} páginas cargadas.")
    return documentos

def crear_vectorstore(documentos):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100
    )
    chunks = splitter.split_documents(documentos)
    print(f"{len(chunks)} chunks creados.")

    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    vectorstore = Chroma.from_documents(
        chunks,
        embeddings,
        persist_directory=CHROMA_PATH
    )
    print("Vectorstore creado.")
    return vectorstore

def buscar_contexto(query: str, vectorstore, k: int = 3) -> str:
    docs = vectorstore.similarity_search(query, k=k)
    contexto = "\n\n".join([doc.page_content for doc in docs])
    return contexto