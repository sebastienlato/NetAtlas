"""Real loopback API for browser acceptance, using a disposable synthetic database."""

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import uvicorn
from inspection_fixture import seed_inspection
from sqlalchemy import create_engine, text

from netatlas.api import create_app
from netatlas.demo import seed
from netatlas.operations.access import provision_access
from netatlas.storage.blobs import BlobStore
from netatlas.storage.database import local_engine, migrate
from netatlas.storage.pipeline import Pipeline


def main() -> None:
    admin = local_engine(Path("data/storage"))
    name = "netatlas_test_web_" + uuid4().hex
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    engine = create_engine(admin.url.set(database=name), hide_parameters=True)
    read = None
    roles: list[str] = []
    try:
        with tempfile.TemporaryDirectory() as temp:
            migrate(engine)
            pipeline = Pipeline(engine, BlobStore(Path(temp) / "blobs"))
            sha = seed(pipeline, datetime.now(UTC))
            seed_inspection(pipeline, sha)
            Path(".cache").mkdir(exist_ok=True)
            Path(".cache/web-demo.json").write_text(json.dumps({"dataset_sha256": sha}))
            access = Path(temp) / "services"
            provision_access(engine, access)
            read = local_engine(access / "read")
            roles = [
                json.loads((access / kind / "connection.json").read_text())["username"]
                for kind in ("read", "control")
            ]
            uvicorn.run(
                create_app(engine=read, blobs=pipeline.blobs, web_root=Path("web/dist")),
                host="127.0.0.1",
                port=8000,
                proxy_headers=False,
                access_log=False,
                log_level="warning",
            )
    finally:
        if read is not None:
            read.dispose()
        engine.dispose()
        with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
            for role in roles:
                connection.execute(text(f'DROP ROLE "{role}"'))
        admin.dispose()


if __name__ == "__main__":
    main()
