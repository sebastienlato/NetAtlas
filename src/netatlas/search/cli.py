"""Private local JSON query/output boundary; console reports counts only."""

import argparse
import json
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from netatlas.derivations.offline import json_object, regular_file
from netatlas.enrichment.offline import publish
from netatlas.search.models import Query
from netatlas.search.service import search
from netatlas.storage.database import local_engine

QUERY_BYTES = 16384


def read_query(path: Path) -> Query:
    with regular_file(path) as stream:
        data = stream.read(QUERY_BYTES + 1)
    if len(data) > QUERY_BYTES:
        raise ValueError("query size limit")
    return Query.model_validate(json_object(data))


def main() -> None:
    parser = argparse.ArgumentParser(prog="netatlas-search")
    parser.add_argument("--root", type=Path, default=Path("data/storage"))
    parser.add_argument("--query", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        query = read_query(args.query)
        engine = local_engine(args.root)
        try:
            result = search(engine, query)
            encoded = json.dumps(result, ensure_ascii=True).encode() + b"\n"
            if len(encoded) > 4 * 1024 * 1024:
                raise ValueError("output size limit")
            publish(args.output, encoded)
            print(
                json.dumps(
                    {key: result[key] for key in ("endpoints", "observations", "candidates")}
                )
            )
        finally:
            engine.dispose()
    except ValueError, OSError, SQLAlchemyError, RecursionError, TypeError, KeyError, OverflowError:
        parser.exit(2, "Search failed; inspect local setup, query limits and output path.\n")
