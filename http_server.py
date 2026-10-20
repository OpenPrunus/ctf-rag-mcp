#!/usr/bin/env python3
"""Sert search_writeups() en HTTP (stdlib uniquement), pour un déploiement centralisé — même
corpus et même logique que rag_server.py (MCP stdio), mais accessible en réseau à plusieurs
clients légers sans qu'ils aient à porter le corpus ni les dépendances de recherche.

Recharge le corpus si le fichier a changé depuis le dernier chargement (mtime), sans redémarrage.
"""
import json, os, re, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from rank_bm25 import BM25Okapi

CORPUS_PATH = os.environ.get("CTF_RAG_CORPUS_PATH", "/data/corpus.json")
EXCERPT_LEN = int(os.environ.get("CTF_RAG_EXCERPT_LEN", "1500"))
INDEX_CHARS = int(os.environ.get("CTF_RAG_INDEX_CHARS", "5000"))
PORT = int(os.environ.get("CTF_RAG_HTTP_PORT", "8090"))

_state = {"mtime": 0.0, "corpus": [], "bm25": None}


def tok(t):
    return re.findall(r"[a-zA-Z0-9_]+", t.lower())


def reload_if_changed():
    try:
        mtime = os.path.getmtime(CORPUS_PATH)
    except FileNotFoundError:
        return
    if mtime == _state["mtime"]:
        return
    docs = json.load(open(CORPUS_PATH, encoding="utf-8"))
    for d in docs:
        d.setdefault("category", "")
        d.setdefault("source", "")
        d.setdefault("outcome", None)
        d.setdefault("difficulty", "")
    corpus_tok = [tok(d["text"][:INDEX_CHARS] + " " + d.get("title", "")) for d in docs]
    _state.update(mtime=mtime, corpus=docs, bm25=BM25Okapi(corpus_tok) if docs else None)
    print(f"[ctf-rag-http] rechargé {len(docs)} documents depuis {CORPUS_PATH}", flush=True)


def search_writeups(query: str, top_k: int = 5, category: str | None = None, only_solved: bool = False):
    reload_if_changed()
    if _state["bm25"] is None:
        return []
    import numpy as np

    scores = _state["bm25"].get_scores(tok(query))
    idx = list(np.argsort(-scores))
    out = []
    for i in idx:
        d = _state["corpus"][i]
        if category and d.get("category", "").lower() != category.lower():
            continue
        if only_solved and d.get("outcome") not in ("solved", None):
            continue
        if scores[i] <= 0:
            continue
        out.append(
            dict(
                score=round(float(scores[i]), 2),
                title=d.get("title", ""),
                category=d.get("category", ""),
                source=d.get("source", ""),
                outcome=d.get("outcome"),
                difficulty=d.get("difficulty", ""),
                excerpt=d.get("text", "")[:EXCERPT_LEN],
            )
        )
        if len(out) >= top_k:
            break
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # silence par défaut, docker logs capte déjà stdout/stderr utiles

    def do_GET(self):
        if self.path == "/health":
            reload_if_changed()
            self._json(200, {"status": "ok", "documents": len(_state["corpus"])})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/search":
            return self._json(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            results = search_writeups(
                query=body["query"],
                top_k=body.get("top_k", 5),
                category=body.get("category"),
                only_solved=body.get("only_solved", False),
            )
            self._json(200, {"results": results})
        except Exception as e:
            self._json(400, {"error": str(e)})

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    reload_if_changed()
    print(f"[ctf-rag-http] écoute sur 0.0.0.0:{PORT} (corpus: {CORPUS_PATH})", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
