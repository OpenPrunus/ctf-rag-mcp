#!/usr/bin/env python3
"""Pont client : parle MCP (stdio) côté client, relaie en HTTP vers un serveur ctf-rag centralisé
(http_server.py). Aucune dépendance externe (stdlib uniquement) — pas de venv, pas de Docker côté
client, exactement le rôle que joue `mcp-searxng` pour SearXNG.

Variable d'environnement : CTF_RAG_URL (ex. http://192.168.1.44:8090), défaut http://localhost:8090.
"""
import json, os, sys, urllib.request

URL = os.environ.get("CTF_RAG_URL", "http://localhost:8090").rstrip("/")

TOOL_DEF = {
    "name": "search_writeups",
    "description": (
        "Recherche dans un corpus de documents (à l'origine : writeups CTF réels, succès et "
        "échecs) une technique/situation similaire à celle rencontrée. Utilise des mots-clés "
        "techniques précis (nom d'outil, type de faille, fonction suspecte) plutôt qu'une phrase "
        "vague — la recherche est lexicale (BM25), pas sémantique."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Mots-clés techniques précis"},
            "top_k": {"type": "integer", "description": "Nombre de résultats (défaut 5)"},
            "category": {"type": "string", "description": "Filtrer par catégorie exacte du corpus"},
            "only_solved": {"type": "boolean", "description": "Ne garder que outcome=solved"},
        },
        "required": ["query"],
    },
}


def call_remote(args):
    data = json.dumps(args).encode()
    req = urllib.request.Request(f"{URL}/search", data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)["results"]


def main():
    sys.stderr.write(f"[ctf-rag-bridge] relais vers {URL}\n")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue
        mid, method = req.get("id"), req.get("method")
        if method == "initialize":
            resp = {
                "jsonrpc": "2.0", "id": mid,
                "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                           "serverInfo": {"name": "ctf-rag-bridge", "version": "0.1"}},
            }
        elif method == "tools/list":
            resp = {"jsonrpc": "2.0", "id": mid, "result": {"tools": [TOOL_DEF]}}
        elif method == "tools/call":
            args = req.get("params", {}).get("arguments", {})
            try:
                text = json.dumps(call_remote(args), ensure_ascii=False, indent=1)
            except Exception as e:
                text = f"Erreur (serveur {URL} injoignable ?): {e}"
            resp = {"jsonrpc": "2.0", "id": mid, "result": {"content": [{"type": "text", "text": text}]}}
        else:
            resp = {"jsonrpc": "2.0", "id": mid, "result": {}}
        print(json.dumps(resp), flush=True)


if __name__ == "__main__":
    main()
