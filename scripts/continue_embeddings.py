"""Validate and ingest current artifacts; optionally resume missing/mismatched docs.
Existing artifacts lack model provenance; source/vector validation is not model attestation.
Writes regenerated artifacts under --state, never modifies the source checkout.
"""
import argparse
import hashlib
import json
import math
import os
import time
from pathlib import Path


def chunks(text):
    result = []
    start = 0
    while start < len(text):
        end = min(start + 1200, len(text))
        if text[start:end].strip():
            result.append(text[start:end].strip())
        if end == len(text):
            break
        start = end - 200
    return result


def valid(doc, source):
    if any(doc.get(k) != source.get(k) for k in ('id', 'url', 'title')):
        return False
    rows = doc.get('chunks', [])
    if not rows or [r.get('text') for r in rows] != chunks(source['text']):
        return False
    for i, row in enumerate(rows):
        v = row.get('embedding', [])
        if row.get('chunk_index') != i or len(v) != 1024:
            return False
        if any(isinstance(x, bool) or not isinstance(x, (float, int)) or not math.isfinite(x) for x in v) or not any(v):
            return False
    return True


def write(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value), encoding='utf-8')
    tmp.replace(path)


def read(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def main():
    from dotenv import dotenv_values
    import psycopg2
    from openai import OpenAI
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', required=True, type=Path)
    p.add_argument('--state', type=Path, default=Path(__file__).resolve().parents[1] / 'outputs' / 'resumed-embeddings')
    p.add_argument('--resume', action='store_true')
    args = p.parse_args()
    cfg = dotenv_values(args.repo / '.env')
    model = cfg.get('OPENROUTER_MODEL')
    if model != 'liquid/lfm-2.5-embedding-350m:free':
        raise SystemExit('Expected the existing free Liquid embedding model; no paid fallback allowed.')
    args.state.mkdir(parents=True, exist_ok=True)
    conn = psycopg2.connect(host=cfg.get('DB_HOST', 'localhost'), port=cfg.get('DB_PORT', '5432'), dbname=cfg.get('DB_NAME', 'football_intelligence'), user=cfg.get('DB_USER', 'postgres'), password=cfg.get('DB_PASSWORD'), connect_timeout=10)
    def ingest(doc):
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT atttypmod FROM pg_attribute WHERE attrelid='football_chunks'::regclass AND attname='embedding'")
                if cur.fetchone() != (1024,):
                    raise RuntimeError('Database must use vector(1024)')
                cur.execute('DELETE FROM football_chunks WHERE doc_id=%s', (doc['id'],))
                cur.executemany('INSERT INTO football_chunks(doc_id,chunk_index,url,title,text,embedding) VALUES (%s,%s,%s,%s,%s,%s::vector)', [(doc['id'], r['chunk_index'], doc['url'], doc['title'], r['text'], json.dumps(r['embedding'])) for r in doc['chunks']])
    pending = []
    loaded = 0
    for path in sorted((args.repo / 'data/clean').glob('*.json')):
        source = read(path)
        candidates = [read(args.state / path.name), read(args.repo / 'data/embeddings' / path.name)]
        artifact = next((d for d in candidates if valid(d, source)), None)
        if artifact is not None:
            ingest(artifact)
            loaded += 1
        else:
            pending.append((path.name, source))
    print(f'Loaded {loaded} source-matching documents; {len(pending)} need embeddings.', flush=True)
    write(args.state / 'pending.json', {'documents': [name for name, _ in pending]})
    if args.resume:
        client = OpenAI(api_key=cfg.get('OPENAI_API_KEY'), base_url='https://openrouter.ai/api/v1', max_retries=0, timeout=60)
        try:
            for name, source in pending:
                texts = chunks(source['text'])
                signature = hashlib.sha256(json.dumps([model, texts]).encode()).hexdigest()
                partial_path = args.state / (name + '.partial')
                partial = read(partial_path)
                vectors = partial.get('vectors', []) if partial.get('signature') == signature else []
                for start in range(len(vectors), len(texts), 10):
                    response = client.embeddings.create(model=model, input=texts[start:start+10])
                    items = sorted(response.data, key=lambda r: r.index)
                    expected = len(texts[start:start+10])
                    if [r.index for r in items] != list(range(expected)):
                        raise RuntimeError('Incomplete or misindexed API response')
                    batch = [r.embedding for r in items]
                    if any(len(v) != 1024 or not all(math.isfinite(x) for x in v) or not any(v) for v in batch):
                        raise RuntimeError('Invalid API vectors')
                    vectors.extend(batch)
                    write(partial_path, {'signature': signature, 'vectors': vectors})
                    time.sleep(4)
                artifact = {k: source[k] for k in ('id', 'url', 'title')}
                artifact['chunks'] = [{'chunk_index': i, 'text': t, 'embedding': v} for i, (t,v) in enumerate(zip(texts,vectors))]
                artifact['embedding_metadata'] = {'model': model, 'dimension': 1024, 'signature': signature}
                if not valid(artifact, source):
                    raise RuntimeError('Generated artifact failed validation')
                write(args.state / name, artifact)
                ingest(artifact)
                print('Embedded and ingested ' + name, flush=True)
        except Exception as exc:
            # Do not print provider response bodies or credentials.
            print(f'Resume stopped: {type(exc).__name__}, status {getattr(exc,"status_code",None)}. Completed batches preserved.', flush=True)
            if getattr(exc, 'status_code', None) == 429:
                print('Provider quota/rate limit reached. Rerun later to resume.', flush=True)
            else:
                raise
        finally:
            client.close()
    with conn.cursor() as cur:
        cur.execute('SELECT COUNT(*), COUNT(DISTINCT doc_id) FROM football_chunks')
        rows, docs = cur.fetchone()
    conn.close()
    remaining = [name for name, source in pending if not valid(read(args.state / name), source)]
    write(args.state / 'pending.json', {'documents': remaining})
    print(f'Database now has {rows} chunks across {docs} documents; {len(remaining)} pending.', flush=True)

if __name__ == '__main__':
    main()
