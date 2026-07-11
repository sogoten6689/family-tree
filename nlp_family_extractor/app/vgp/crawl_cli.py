from __future__ import annotations

import argparse
import json
import sys

from app.database import database_enabled, get_db, init_database
from app.documents.storage import ObjectStorage
from app.family_tree_store import MySqlFamilyTreeStore
from app.vgp.bootstrap import bootstrap_vgp
from app.vgp.crawl_service import VgpCrawlOptions, VgpCrawlService


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Crawl VietnamGiaPha V2 into MySQL + MinIO")
    parser.add_argument("--start-id", type=int, required=True)
    parser.add_argument("--end-id", type=int, default=None)
    parser.add_argument(
        "--modules",
        default="giapha,pha_ky,pha_he,images",
        help="Comma-separated modules",
    )
    parser.add_argument("--skip-unchanged", action="store_true", default=True)
    parser.add_argument("--no-skip-unchanged", dest="skip_unchanged", action="store_false")
    parser.add_argument("--attach-documents", action="store_true", default=True)
    parser.add_argument("--no-attach-documents", dest="attach_documents", action="store_false")
    parser.add_argument("--sync-pipeline", action="store_true", default=True)
    parser.add_argument("--no-sync-pipeline", dest="sync_pipeline", action="store_false")
    parser.add_argument("--delay-seconds", type=float, default=0.2)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    end_id = args.end_id if args.end_id is not None else args.start_id

    init_database()
    if not database_enabled():
        print("MySQL is not configured (MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD).", file=sys.stderr)
        return 1

    bootstrap_vgp()
    store = MySqlFamilyTreeStore.from_env()

    storage = None
    if args.attach_documents:
        storage = ObjectStorage.from_env()
        if not storage.config.enabled:
            print("MinIO is not configured — continuing without document attach.", file=sys.stderr)
            storage = None

    db = next(get_db())
    try:
        service = VgpCrawlService(
            db=db,
            storage=storage,
            get_tree=store.get_tree,
        )
        summary = service.crawl_range(
            start_id=args.start_id,
            end_id=end_id,
            options=VgpCrawlOptions(
                modules={item.strip() for item in args.modules.split(",") if item.strip()},
                skip_unchanged=args.skip_unchanged,
                attach_documents=args.attach_documents and storage is not None,
                sync_pipeline=args.sync_pipeline,
                delay_seconds=args.delay_seconds,
            ),
        )
        db.commit()
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if not summary.get("errors") else 2
    except Exception as exc:
        db.rollback()
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
