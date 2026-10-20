FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY rag_server.py .

ENV CTF_RAG_CORPUS_PATH=/data/corpus.json
VOLUME ["/data"]

# Serveur MCP stdio : destiné à être lancé via `docker run -i`, pas `-d`
# (le protocole MCP stdio a besoin d'un stdin/stdout connecté en continu).
ENTRYPOINT ["python3", "rag_server.py"]
