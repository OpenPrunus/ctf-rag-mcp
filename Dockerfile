FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY rag_server.py http_server.py mcp_http_bridge.py .

ENV CTF_RAG_CORPUS_PATH=/data/corpus.json
VOLUME ["/data"]

# Mode par défaut : serveur MCP stdio, lancé via `docker run -i` (pas `-d` — le protocole
# MCP stdio a besoin d'un stdin/stdout connecté en continu).
# Pour le mode HTTP centralisé (service long-running, `restart: unless-stopped`), surcharger
# la commande : `docker run -d -p 8090:8090 ... openprunus/ctf-rag-mcp python3 http_server.py`
ENTRYPOINT ["python3"]
CMD ["rag_server.py"]
