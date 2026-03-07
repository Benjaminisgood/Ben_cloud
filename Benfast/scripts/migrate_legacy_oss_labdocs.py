from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from services.labdocs_legacy_migration import LegacyLabdocsMigrator
from services.labdocs_service import LabDocsService
from services.labdocs_storage import AliyunOSSStorageBackend
from settings import settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate legacy benfast/labdocs OSS objects into the new benfast flat layout.",
    )
    parser.add_argument(
        "--legacy-prefix",
        default="benfast/labdocs",
        help="Legacy OSS prefix to import from.",
    )
    parser.add_argument(
        "--target-prefix",
        default=settings.LABDOCS_STORAGE_PREFIX,
        help="Target OSS prefix to write to.",
    )
    parser.add_argument(
        "--skip-rebuild",
        action="store_true",
        help="Skip unified docs site rebuild after migration.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    legacy_storage = AliyunOSSStorageBackend(
        endpoint=settings.ALIYUN_OSS_ENDPOINT,
        access_key_id=settings.ALIYUN_OSS_ACCESS_KEY_ID,
        access_key_secret=settings.ALIYUN_OSS_ACCESS_KEY_SECRET,
        bucket_name=settings.ALIYUN_OSS_BUCKET,
        prefix=args.legacy_prefix,
    )
    target_storage = AliyunOSSStorageBackend(
        endpoint=settings.ALIYUN_OSS_ENDPOINT,
        access_key_id=settings.ALIYUN_OSS_ACCESS_KEY_ID,
        access_key_secret=settings.ALIYUN_OSS_ACCESS_KEY_SECRET,
        bucket_name=settings.ALIYUN_OSS_BUCKET,
        prefix=args.target_prefix,
    )
    target_service = LabDocsService(
        storage=target_storage,
        publish_root=Path(settings.LABDOCS_PUBLISH_ROOT),
    )
    migrator = LegacyLabdocsMigrator(
        legacy_storage=legacy_storage,
        target_service=target_service,
    )
    stats = migrator.migrate(rebuild_site=not args.skip_rebuild)
    print(
        json.dumps(
            {
                "books_migrated": stats.books_migrated,
                "pages_migrated": stats.pages_migrated,
                "assets_migrated": stats.assets_migrated,
                "publishes_migrated": stats.publishes_migrated,
                "rebuilt_site": stats.rebuilt_site,
                "published_books": stats.published_books,
                "legacy_prefix": args.legacy_prefix,
                "target_prefix": args.target_prefix,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
