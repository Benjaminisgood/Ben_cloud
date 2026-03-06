from __future__ import annotations

import ast
import contextlib
import logging
import re
from pathlib import Path

from sqlalchemy import inspect, text

from benoss_api.core.config import get_settings
from benoss_api.db.session import engine

logger = logging.getLogger(__name__)

_REVISION_RE = re.compile(r"^revision\s*=\s*['\"]([^'\"]+)['\"]", re.MULTILINE)
_DOWN_REVISION_RE = re.compile(r"^down_revision\s*=\s*(.+)$", re.MULTILINE)
_AUTO_FIXABLE_CODES = {"schema_not_initialized", "version_table_empty", "not_at_head"}

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None


class MigrationStateError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _api_dir() -> Path:
    return Path(__file__).resolve().parents[3]


def _versions_dir() -> Path:
    return _api_dir() / "alembic" / "versions"


def _alembic_ini_path() -> Path:
    return _api_dir() / "alembic.ini"


def _alembic_script_dir() -> Path:
    return _api_dir() / "alembic"


def _migration_lock_path() -> Path:
    return get_settings().DATA_DIR / ".alembic-upgrade.lock"


def _parse_revision_file(path: Path) -> tuple[str | None, object | None]:
    text_content = path.read_text(encoding="utf-8")

    revision_match = _REVISION_RE.search(text_content)
    if not revision_match:
        return None, None
    revision = revision_match.group(1).strip()

    down_revision: object | None = None
    down_match = _DOWN_REVISION_RE.search(text_content)
    if down_match:
        raw = down_match.group(1).strip()
        if raw == "None":
            down_revision = None
        else:
            try:
                down_revision = ast.literal_eval(raw)
            except (SyntaxError, ValueError):
                down_revision = raw.strip("'\"")
    return revision, down_revision


def _flatten_down_revisions(value: object | None) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        token = value.strip()
        return {token} if token else set()
    if isinstance(value, (tuple, list, set)):
        out: set[str] = set()
        for item in value:
            if isinstance(item, str) and item.strip():
                out.add(item.strip())
        return out
    return set()


def _collect_revision_graph() -> tuple[set[str], set[str]]:
    versions_dir = _versions_dir()
    if not versions_dir.exists():
        return set(), set()

    revisions: set[str] = set()
    down_revisions: set[str] = set()

    for path in versions_dir.glob("*.py"):
        if path.name.startswith("__"):
            continue
        revision, down_revision = _parse_revision_file(path)
        if not revision:
            continue
        revisions.add(revision)
        down_revisions.update(_flatten_down_revisions(down_revision))

    heads = revisions - down_revisions if revisions else set()
    return revisions, heads


def _validate_migration_state(revisions: set[str], heads: set[str]) -> None:
    with engine.connect() as conn:
        table_names = set(inspect(conn).get_table_names())
        has_version_table = "alembic_version" in table_names
        app_tables = {name for name in table_names if name != "alembic_version" and not name.startswith("sqlite_")}

        if not has_version_table:
            head_hint = ",".join(sorted(heads))
            if app_tables:
                logger.warning(
                    "Database has application tables but no alembic_version table. "
                    "Treating as legacy schema; consider `alembic stamp %s`.",
                    head_hint,
                )
                return
            raise MigrationStateError(
                "schema_not_initialized",
                "Database schema is not initialized. Run `make db-upgrade` before starting the app.",
            )

        rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
        current_revisions = {str(row[0]).strip() for row in rows if row and row[0]}
        if not current_revisions:
            raise MigrationStateError(
                "version_table_empty",
                "alembic_version table is empty. Run `make db-upgrade` to initialize schema version.",
            )

        unknown = current_revisions - revisions
        if unknown:
            raise MigrationStateError(
                "unknown_revision",
                "Database contains unknown Alembic revision(s): "
                f"{sorted(unknown)}. Available revisions: {sorted(revisions)}"
            )

        if heads and current_revisions != heads:
            raise MigrationStateError(
                "not_at_head",
                "Database revision is not at project head. "
                f"current={sorted(current_revisions)}, head={sorted(heads)}. Run `make db-upgrade`."
            )


@contextlib.contextmanager
def _migration_lock() -> object:
    lock_path = _migration_lock_path()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        if fcntl is None:
            logger.warning("fcntl is unavailable; proceeding without migration lock")
            yield
            return
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _upgrade_to_head() -> None:
    from alembic import command
    from alembic.config import Config

    settings = get_settings()
    alembic_cfg = Config(str(_alembic_ini_path()))
    alembic_cfg.set_main_option("script_location", str(_alembic_script_dir()))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    command.upgrade(alembic_cfg, "head")


def ensure_migration_state(*, auto_upgrade: bool = False) -> None:
    revisions, heads = _collect_revision_graph()
    if not revisions:
        logger.warning("No Alembic revisions found under %s; skipping migration state check", _versions_dir())
        return

    try:
        _validate_migration_state(revisions, heads)
        return
    except MigrationStateError as exc:
        if not auto_upgrade or exc.code not in _AUTO_FIXABLE_CODES:
            raise RuntimeError(str(exc)) from exc

    with _migration_lock():
        try:
            _validate_migration_state(revisions, heads)
            return
        except MigrationStateError as locked_exc:
            if locked_exc.code not in _AUTO_FIXABLE_CODES:
                raise RuntimeError(str(locked_exc)) from locked_exc
            logger.info(
                "Auto-upgrading database schema to Alembic head due to migration state: %s",
                locked_exc.code,
            )
            _upgrade_to_head()
            _validate_migration_state(revisions, heads)
