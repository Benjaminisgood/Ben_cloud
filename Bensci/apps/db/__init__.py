from sqlalchemy import inspect, text

from apps.db.models import Base
from apps.db.session import engine


def _ensure_article_columns() -> None:
    with engine.begin() as conn:
        inspector = inspect(conn)
        if "articles" not in inspector.get_table_names():
            return

        columns = {col["name"] for col in inspector.get_columns("articles")}

        if "check_status" not in columns:
            conn.execute(
                text("ALTER TABLE articles ADD COLUMN check_status VARCHAR(16) NOT NULL DEFAULT 'unchecked'")
            )
        conn.execute(
            text("UPDATE articles SET check_status = 'unchecked' WHERE check_status IS NULL OR check_status = ''")
        )
        if "citation_count" not in columns:
            conn.execute(text("ALTER TABLE articles ADD COLUMN citation_count INTEGER"))
        if "impact_factor" not in columns:
            conn.execute(text("ALTER TABLE articles ADD COLUMN impact_factor FLOAT"))
        if "embedding_vector" not in columns:
            conn.execute(text("ALTER TABLE articles ADD COLUMN embedding_vector BLOB"))
        if "embedding_model" not in columns:
            conn.execute(text("ALTER TABLE articles ADD COLUMN embedding_model VARCHAR(128)"))
        if "embedding_dimensions" not in columns:
            conn.execute(text("ALTER TABLE articles ADD COLUMN embedding_dimensions INTEGER"))
        if "embedding_text_hash" not in columns:
            conn.execute(text("ALTER TABLE articles ADD COLUMN embedding_text_hash VARCHAR(64)"))
        if "embedding_updated_at" not in columns:
            conn.execute(text("ALTER TABLE articles ADD COLUMN embedding_updated_at DATETIME"))
        if "ingested_at" not in columns:
            conn.execute(text("ALTER TABLE articles ADD COLUMN ingested_at DATETIME"))
        if "note" not in columns:
            conn.execute(text("ALTER TABLE articles ADD COLUMN note TEXT DEFAULT ''"))
        conn.execute(text("UPDATE articles SET note = '' WHERE note IS NULL"))
        conn.execute(
            text(
                "UPDATE articles "
                "SET ingested_at = COALESCE(created_at, CURRENT_TIMESTAMP) "
                "WHERE ingested_at IS NULL"
            )
        )
        if "updated_at" in columns:
            conn.execute(
                text(
                    "UPDATE articles "
                    "SET ingested_at = updated_at "
                    "WHERE updated_at IS NOT NULL AND (ingested_at IS NULL OR updated_at > ingested_at)"
                )
            )


def _ensure_task_columns() -> None:
    with engine.begin() as conn:
        inspector = inspect(conn)
        if "tasks" not in inspector.get_table_names():
            return

        columns = {col["name"] for col in inspector.get_columns("tasks")}
        if "log_text" not in columns:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN log_text TEXT DEFAULT ''"))
        if "result_json" not in columns:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN result_json TEXT DEFAULT '{}'"))
        if "payload_json" not in columns:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN payload_json TEXT DEFAULT '{}'"))
        if "error" not in columns:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN error TEXT DEFAULT ''"))
        if "started_at" not in columns:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN started_at DATETIME"))
        if "finished_at" not in columns:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN finished_at DATETIME"))
        if "updated_at" not in columns:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN updated_at DATETIME"))
            conn.execute(text("UPDATE tasks SET updated_at = COALESCE(created_at, CURRENT_TIMESTAMP) WHERE updated_at IS NULL"))


def _articles_fts_has_note_column(conn) -> bool:
    rows = conn.execute(text("PRAGMA table_info(articles_fts)")).mappings().all()
    columns = {str(row.get("name") or "").strip().lower() for row in rows}
    return "note" in columns


def _ensure_fts_objects(*, force_rebuild: bool = False) -> None:
    with engine.begin() as conn:
        has_fts_table = bool(
            conn.execute(
                text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='articles_fts' LIMIT 1")
            ).scalar()
        )
        requires_schema_upgrade = has_fts_table and not _articles_fts_has_note_column(conn)
        if requires_schema_upgrade:
            conn.execute(text("DROP TRIGGER IF EXISTS articles_fts_au"))
            conn.execute(text("DROP TRIGGER IF EXISTS articles_fts_ad"))
            conn.execute(text("DROP TRIGGER IF EXISTS articles_fts_ai"))
            conn.execute(text("DROP TABLE IF EXISTS articles_fts"))

        conn.execute(
            text(
                "CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5("
                "article_id UNINDEXED, "
                "doi, title, keywords, abstract, journal, corresponding_author, affiliations, publisher, note)"
            )
        )
        conn.execute(
            text(
                "CREATE TRIGGER IF NOT EXISTS articles_fts_ai AFTER INSERT ON articles BEGIN "
                "INSERT INTO articles_fts(article_id, doi, title, keywords, abstract, journal, corresponding_author, affiliations, publisher, note) "
                "VALUES (new.id, COALESCE(new.doi,''), COALESCE(new.title,''), COALESCE(new.keywords,''), COALESCE(new.abstract,''), "
                "COALESCE(new.journal,''), COALESCE(new.corresponding_author,''), COALESCE(new.affiliations,''), COALESCE(new.publisher,''), COALESCE(new.note,'')); "
                "END"
            )
        )
        conn.execute(
            text(
                "CREATE TRIGGER IF NOT EXISTS articles_fts_ad AFTER DELETE ON articles BEGIN "
                "DELETE FROM articles_fts WHERE article_id = old.id; "
                "END"
            )
        )
        conn.execute(
            text(
                "CREATE TRIGGER IF NOT EXISTS articles_fts_au AFTER UPDATE ON articles BEGIN "
                "DELETE FROM articles_fts WHERE article_id = old.id; "
                "INSERT INTO articles_fts(article_id, doi, title, keywords, abstract, journal, corresponding_author, affiliations, publisher, note) "
                "VALUES (new.id, COALESCE(new.doi,''), COALESCE(new.title,''), COALESCE(new.keywords,''), COALESCE(new.abstract,''), "
                "COALESCE(new.journal,''), COALESCE(new.corresponding_author,''), COALESCE(new.affiliations,''), COALESCE(new.publisher,''), COALESCE(new.note,'')); "
                "END"
            )
        )

        article_count = conn.execute(text("SELECT COUNT(*) FROM articles")).scalar_one()
        fts_count = conn.execute(text("SELECT COUNT(*) FROM articles_fts")).scalar_one()
        if force_rebuild or requires_schema_upgrade or fts_count != article_count:
            conn.execute(text("DELETE FROM articles_fts"))
            conn.execute(
                text(
                    "INSERT INTO articles_fts(article_id, doi, title, keywords, abstract, journal, corresponding_author, affiliations, publisher, note) "
                    "SELECT id, COALESCE(doi,''), COALESCE(title,''), COALESCE(keywords,''), COALESCE(abstract,''), COALESCE(journal,''), "
                    "COALESCE(corresponding_author,''), COALESCE(affiliations,''), COALESCE(publisher,''), COALESCE(note,'') "
                    "FROM articles"
                )
            )


def create_all() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_article_columns()
    _ensure_task_columns()
    _ensure_fts_objects()


def rebuild_fts_index() -> None:
    _ensure_fts_objects(force_rebuild=True)
