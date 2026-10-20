# ctf-rag-mcp

A minimal MCP (stdio) server that performs **lexical search** (BM25) over a user-provided corpus
of text documents — originally built to let an autonomous AI agent query a corpus of CTF writeups
(both solved and failed attempts), but the format is generic.

This repository ships **no dataset**: you bring your own (see `corpus_examples/` for the expected
format and a small working example).

## Why BM25 instead of semantic embeddings

On a corpus of dense technical jargon (tool names, function names, CVEs, rare terms like
"needle", "mergedeep", "prototype pollution"), a small general-purpose embedding model tends to
produce generically high similarity scores for any technical text, without real topical
discrimination — tested in practice: a completely unrelated writeup scored *higher* on semantic
similarity than the actually relevant one, because shared technical vocabulary ("exploit",
"payload", "flag"...) dominated the signal.

Exact lexical search (BM25) proved noticeably more reliable for this use case: a precise, rare
term matches directly, without dilution.

## Corpus format

A JSON file, a list of objects:

```json
[
  {
    "id": "optional",
    "title": "required",
    "category": "optional, used by the --category filter",
    "source": "optional, shown in results",
    "outcome": "optional, e.g. solved / failed",
    "difficulty": "optional",
    "text": "required — the indexed content, also returned as an excerpt"
  }
]
```

See `corpus_examples/sample_corpus.json` for a minimal example (3 fictional documents).

## Usage

### Locally (without Docker)

```bash
pip install -r requirements.txt
CTF_RAG_CORPUS_PATH=./corpus_examples/sample_corpus.json python3 rag_server.py
```

The server speaks MCP over stdio (line-delimited JSON-RPC) — it isn't meant to be typed at
directly, but launched by an MCP client (see below).

### With Docker

```bash
docker pull openprunus/ctf-rag-mcp:latest
docker run -i --rm -v "$(pwd)/corpus_examples/sample_corpus.json:/data/corpus.json:ro" openprunus/ctf-rag-mcp
```

(`-i` is required: the MCP stdio protocol needs a continuously connected stdin/stdout — don't use
`-d`.)

### MCP client configuration (example: opencode)

```json
{
  "mcp": {
    "ctf-rag": {
      "type": "local",
      "command": [
        "docker", "run", "-i", "--rm",
        "-v", "/path/to/my_corpus.json:/data/corpus.json:ro",
        "openprunus/ctf-rag-mcp"
      ],
      "enabled": true
    }
  }
}
```

Or without Docker, by pointing directly at the Python script with the `CTF_RAG_CORPUS_PATH`
environment variable.

## Exposed tool

`search_writeups(query, top_k=5, category=None, only_solved=False)` — BM25 search over the
corpus, returns the `top_k` most relevant documents (score, title, category, source, `outcome`,
excerpt).

## Environment variables

| Variable | Default | Role |
|---|---|---|
| `CTF_RAG_CORPUS_PATH` | `/data/corpus.json` | Path to the corpus file |
| `CTF_RAG_EXCERPT_LEN` | `1500` | Max excerpt length returned per result |
| `CTF_RAG_INDEX_CHARS` | `5000` | Characters of `text` indexed per document (performance) |

## License

MIT.
