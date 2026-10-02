# Manual Testing

Hands-on checks that use live providers, as opposed to the offline `pytest` suite. Activate the project's Python environment and run from the repository root. Keep keys in `.env`, never in commands or committed files.

The automated suite runs offline with network access blocked:

```bash
python -m pytest tests -q
```

## Interactive agent console

`python scripts/test_agents.py --repo .`

Use `both: QUESTION`, `tactical: QUESTION`, or `statistical: QUESTION`. Each persona has separate session memory. Tools include knowledge_search, calculator, and web_search. The configured chat provider may have quotas; this is not an offline test. Exit and restart after changing `.env`.

## Resumable embedding and ingestion

`python scripts/continue_embeddings.py --repo .`

This validates source identity, exact chunk text, indices, and finite nonzero 1024-dimensional vectors before upserting matching documents into the existing PostgreSQL schema. It requires the configured free Liquid model. Legacy vectors do not record their generating model; numeric validity alone cannot establish model compatibility. Use only with the known Liquid corpus. Writes for each document are transactional and replace that document's previous rows.

Add `--resume` to generate missing/mismatched artifacts and ingest each completed document. Completed batches are saved separately under `outputs/resumed-embeddings`; the original corpus is untouched. Rate-limit errors stop the run so it can be rerun after reset; this script does not schedule or wait through a daily quota. Reuse the same `--state` directory across runs. Existing external helper state can be supplied explicitly with `--state PATH`.

## Offline discussion viewer

`python scripts/render_discussion.py outputs/DISCUSSION_ID.json`

Open the resulting `.html` file in a browser, not a text editor. The offline reader filters rounds and analysts and expands sources/tool records. It makes no API calls. Rendering a discussion does not verify its claims.
