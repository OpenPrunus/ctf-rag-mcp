# ctf-rag-mcp

Un serveur MCP (stdio) minimaliste qui fait de la recherche **lexicale** (BM25) dans un corpus de
documents texte fourni par l'utilisateur — à l'origine conçu pour interroger un corpus de writeups
CTF (succès et échecs) depuis un agent IA autonome, mais le format est générique.

Ce dépôt ne contient **aucun dataset** : vous fournissez le vôtre (voir `corpus_examples/` pour le
format attendu et un petit exemple fonctionnel).

## Pourquoi BM25 plutôt que des embeddings sémantiques

Sur un corpus de jargon technique dense (noms d'outils, noms de fonctions, CVE, termes rares comme
« needle », « mergedeep », « prototype pollution »), un petit modèle d'embeddings généraliste a
tendance à produire des scores de similarité génériquement élevés pour tout texte technique, sans
vraie discrimination thématique — testé en pratique : un writeup *sans aucun rapport* peut recevoir
un score de similarité sémantique plus élevé que le writeup réellement pertinent, parce que le
vocabulaire technique partagé (« exploit », « payload », « flag »...) domine le signal.

La recherche lexicale exacte (BM25) s'est montrée nettement plus fiable pour ce cas d'usage : un
terme rare et précis matche directement, sans dilution.

## Format du corpus

Un fichier JSON, liste d'objets :

```json
[
  {
    "id": "optionnel",
    "title": "obligatoire",
    "category": "optionnel, utilisé pour le filtre --category",
    "source": "optionnel, affiché dans les résultats",
    "outcome": "optionnel, ex. solved / failed",
    "difficulty": "optionnel",
    "text": "obligatoire — le contenu indexé et renvoyé en extrait"
  }
]
```

Voir `corpus_examples/sample_corpus.json` pour un exemple minimal (3 documents fictifs).

## Utilisation

### En local (sans Docker)

```bash
pip install -r requirements.txt
CTF_RAG_CORPUS_PATH=./corpus_examples/sample_corpus.json python3 rag_server.py
```

Le serveur parle MCP sur stdio (JSON-RPC ligne par ligne) — il n'est pas destiné à être appelé
directement au clavier, mais lancé par un client MCP (voir plus bas).

### Avec Docker

```bash
docker build -t ctf-rag-mcp .
docker run -i --rm -v "$(pwd)/corpus_examples/sample_corpus.json:/data/corpus.json:ro" ctf-rag-mcp
```

(`-i` est nécessaire : le protocole MCP stdio a besoin d'un stdin/stdout connecté en continu — ne
pas utiliser `-d`.)

### Configuration dans un client MCP (exemple : opencode)

```json
{
  "mcp": {
    "ctf-rag": {
      "type": "local",
      "command": [
        "docker", "run", "-i", "--rm",
        "-v", "/chemin/vers/mon_corpus.json:/data/corpus.json:ro",
        "ctf-rag-mcp"
      ],
      "enabled": true
    }
  }
}
```

Ou sans Docker, en pointant directement sur le script Python et une variable d'environnement
`CTF_RAG_CORPUS_PATH`.

## Outil exposé

`search_writeups(query, top_k=5, category=None, only_solved=False)` — recherche BM25 dans le
corpus, renvoie les `top_k` documents les plus pertinents (score, titre, catégorie, source,
`outcome`, extrait).

## Variables d'environnement

| Variable | Défaut | Rôle |
|---|---|---|
| `CTF_RAG_CORPUS_PATH` | `/data/corpus.json` | Chemin du fichier corpus |
| `CTF_RAG_EXCERPT_LEN` | `1500` | Longueur max de l'extrait renvoyé par résultat |
| `CTF_RAG_INDEX_CHARS` | `5000` | Nombre de caractères de `text` indexés par document (perf) |

## Licence

MIT.
