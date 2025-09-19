import sqlite3
from pathlib import Path


class SnekSQLitePromptLogger:
    TABLE_NAME = "variation_prompts"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "db_name": ("STRING", {"default": "variation_prompts.db"}),
                "original_image_path": ("STRING", {"default": "", "multiline": False}),
                "variation_image_path": ("STRING", {"default": "", "multiline": False}),
                "variation_image_prompt": ("STRING", {"default": "", "multiline": True}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("database_path", "stats")
    FUNCTION = "process"
    CATEGORY = "?? Snek Nodes"

    def process(self, db_name, original_image_path, variation_image_path, variation_image_prompt):
        db_filename = self._normalise_db_name(db_name)
        db_path = self._resolve_db_path(db_filename)

        with sqlite3.connect(db_path) as conn:
            self._ensure_schema(conn)
            conn.execute(
                f"""
                INSERT INTO {self.TABLE_NAME}
                    (original_image_path, variation_image_path, variation_image_prompt)
                VALUES (?, ?, ?)
                """,
                (original_image_path, variation_image_path, variation_image_prompt),
            )
            conn.commit()
            stats_text = self._build_stats(conn)

        return (str(db_path), stats_text)

    def _normalise_db_name(self, raw_name: str) -> str:
        name = raw_name.strip()
        if not name:
            raise ValueError("Database name cannot be empty.")
        if any(sep in name for sep in ("/", "\\", ":")):
            raise ValueError("Database name must not include directory separators.")
        if not name.lower().endswith(".db"):
            name = f"{name}.db"
        return name

    def _resolve_db_path(self, filename: str) -> Path:
        base_dir = Path(__file__).resolve().parents[1]
        return base_dir / filename

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_image_path TEXT NOT NULL,
                variation_image_path TEXT NOT NULL,
                variation_image_prompt TEXT NOT NULL
            )
            """
        )

    def _build_stats(self, conn: sqlite3.Connection) -> str:
        cursor = conn.cursor()
        total_entries = cursor.execute(
            f"SELECT COUNT(*) FROM {self.TABLE_NAME}"
        ).fetchone()[0]
        distinct_originals = cursor.execute(
            f"SELECT COUNT(DISTINCT original_image_path) FROM {self.TABLE_NAME}"
        ).fetchone()[0]
        distinct_variations = cursor.execute(
            f"SELECT COUNT(DISTINCT variation_image_path) FROM {self.TABLE_NAME}"
        ).fetchone()[0]
        distinct_prompts = cursor.execute(
            f"SELECT COUNT(DISTINCT variation_image_prompt) FROM {self.TABLE_NAME}"
        ).fetchone()[0]
        cursor.close()

        stats_lines = [
            f"Total entries: {total_entries}",
            f"Original images tracked: {distinct_originals}",
            f"Variation image paths tracked: {distinct_variations}",
            f"Unique prompts: {distinct_prompts}",
        ]
        return "\n".join(stats_lines)


NODE_CLASS_MAPPINGS = {
    "Snek SQLite Prompt Logger": SnekSQLitePromptLogger,
}
