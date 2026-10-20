#!/usr/bin/env python3
"""Serveur MCP (stdio) : recherche lexicale (BM25) dans un corpus de documents fourni par l'utilisateur.

Conçu à l'origine pour un corpus de writeups CTF (HackTheBox, FCSC, agent traces...), mais le
format de corpus attendu est générique : n'importe quelle collection de documents texte avec
titre/catégorie peut être utilisée (documentation technique, base de connaissances interne...).

Pourquoi BM25 et pas des embeddings sémantiques : sur du jargon technique dense (noms d'outils,
noms de fonctions, CVE, termes rares), la recherche lexicale exacte s'est montrée nettement plus
fiable qu'un petit modèle d'embeddings généraliste, qui a tendance à produire des scores
génériquement élevés pour tout texte technique sans vraie discrimination thématique.

Corpus attendu (JSON, chemin donné par CTF_RAG_CORPUS_PATH, défaut /data/corpus.json) :
  [
    {
      "id": "...",            (optionnel, un identifiant unique)
      "title": "...",         (obligatoire)
      "category": "...",      (optionnel, utilisé pour le filtre --category)
      "source": "...",        (optionnel, affiché dans les résultats)
      "outcome": "...",       (optionnel, ex. "solved"/"failed" pour un corpus de writeups)
      "text": "..."           (obligatoire, le contenu indexé et retourné en extrait)
    },
    ...
  ]
"""
import json, os, re, sys
from rank_bm25 import BM25Okapi

CORPUS_PATH = os.environ.get("CTF_RAG_CORPUS_PATH", "/data/corpus.json")
EXCERPT_LEN = int(os.environ.get("CTF_RAG_EXCERPT_LEN", "1500"))
INDEX_CHARS = int(os.environ.get("CTF_RAG_INDEX_CHARS", "5000"))


def load_corpus(path):
    if not os.path.exists(path):
        sys.stderr.write(
            f"[ctf-rag] ERREUR : corpus introuvable à {path}. "
            f"Monter un fichier JSON via -v <chemin>:{CORPUS_PATH}:ro ou définir CTF_RAG_CORPUS_PATH.\n"
        )
        sys.exit(1)
    docs = json.load(open(path, encoding="utf-8"))
    for d in docs:
        d.setdefault("category", "")
        d.setdefault("source", "")
        d.setdefault("outcome", None)
        d.setdefault("difficulty", "")
    return docs


def tok(t):
    return re.findall(r"[a-zA-Z0-9_]+", t.lower())


CORPUS = load_corpus(CORPUS_PATH)
CORPUS_TOK = [tok(d["text"][:INDEX_CHARS] + " " + d.get("title", "")) for d in CORPUS]
BM25 = BM25Okapi(CORPUS_TOK) if CORPUS else None


def search_writeups(query: str, top_k: int = 5, category: str | None = None, only_solved: bool = False):
    if BM25 is None:
        return []
    import numpy as np

    scores = BM25.get_scores(tok(query))
    idx = list(np.argsort(-scores))
    out = []
    for i in idx:
        d = CORPUS[i]
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
            "only_solved": {
                "type": "boolean",
                "description": "Ne garder que les documents avec outcome=solved (si le corpus a ce champ)",
            },
        },
        "required": ["query"],
    },
}


def main():
    sys.stderr.write(f"[ctf-rag] {len(CORPUS)} documents indexés depuis {CORPUS_PATH}\n")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue
        mid = req.get("id")
        method = req.get("method")
        if method == "initialize":
            resp = {
                "jsonrpc": "2.0",
                "id": mid,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "ctf-rag", "version": "0.1"},
                },
            }
        elif method == "tools/list":
            resp = {"jsonrpc": "2.0", "id": mid, "result": {"tools": [TOOL_DEF]}}
        elif method == "tools/call":
            params = req.get("params", {})
            args = params.get("arguments", {})
            try:
                results = search_writeups(**args)
                text = json.dumps(results, ensure_ascii=False, indent=1)
            except Exception as e:
                text = f"Erreur: {e}"
            resp = {"jsonrpc": "2.0", "id": mid, "result": {"content": [{"type": "text", "text": text}]}}
        else:
            resp = {"jsonrpc": "2.0", "id": mid, "result": {}}
        print(json.dumps(resp), flush=True)


if __name__ == "__main__":
    main()
