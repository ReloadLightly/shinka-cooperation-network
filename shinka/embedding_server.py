#!/usr/bin/env python3
"""Local, genuine Model2Vec embeddings through Shinka's native local backend."""
from __future__ import annotations

import argparse
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import time

MODEL = "minishlab/potion-base-8M"
REVISION = "bf8b056651a2c21b8d2565580b8569da283cab23"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--model-dir", type=Path, default=Path(__file__).parent / "models/potion-base-8M")
    parser.add_argument("--log", type=Path, default=Path("runs/shinka_embedding_calls.jsonl"))
    args = parser.parse_args()
    from model2vec import StaticModel
    model = StaticModel.from_pretrained(str(args.model_dir.resolve()))
    args.log.parent.mkdir(parents=True, exist_ok=True)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"model": MODEL, "revision": REVISION,
                                        "local_only": True}).encode())

        def do_POST(self):
            try:
                if self.path != "/v1/embeddings":
                    raise ValueError("Expected /v1/embeddings")
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 2_000_000:
                    raise ValueError("Request size must be 1..2000000 bytes")
                request = json.loads(self.rfile.read(size))
                inputs = request["input"]
                if isinstance(inputs, str):
                    inputs = [inputs]
                if not inputs or not all(isinstance(x, str) for x in inputs):
                    raise ValueError("Only text embeddings are supported")
                vectors = model.encode(inputs, use_multiprocessing=False)
                data = []
                for index, vector in enumerate(vectors):
                    embedding = vector.tolist()
                    if request.get("encoding_format") == "base64":
                        embedding = base64.b64encode(vector.astype("<f4").tobytes()).decode()
                    data.append({"object": "embedding", "index": index, "embedding": embedding})
                tokens = sum(len(x.split()) for x in inputs)
                response = {"object": "list", "data": data, "model": MODEL,
                            "usage": {"prompt_tokens": tokens, "total_tokens": tokens}}
                with args.log.open("a") as stream:
                    stream.write(json.dumps({"unix_time": time.time(), "num_inputs": len(inputs),
                        "model": MODEL, "revision": REVISION, "billed_api_cost": 0,
                        "usage_token_count_is_whitespace_estimate": True}) + "\n")
                self.send_response(200)
            except Exception as exc:
                response = {"error": {"message": str(exc)}}
                self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
