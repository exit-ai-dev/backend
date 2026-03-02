from typing import Literal, List
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # LLM プロバイダ
    provider: Literal["openai", "echo"] = Field(default="echo", env="PROVIDER")

    # OpenAI 設定
    openai_api_key: str | None = Field(default=None, env="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", env="OPENAI_BASE_URL")
    model: str = Field(default="gpt-4o-mini", env="MODEL")

    # CORS 許可オリジン
    allowed_origins: List[str] = Field(default_factory=lambda: [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ])

    debug: bool = Field(default=True, env="DEBUG")

    # ── File Provider ──────────────────────────────────────────────────────────
    # FILE_PROVIDER=local  (将来: azure_blob / sharepoint / webdav)
    file_provider: str = Field(default="local", env="FILE_PROVIDER")
    local_files_dir: str = Field(default="./uploaded_files", env="LOCAL_FILES_DIR")

    # ── RAG ────────────────────────────────────────────────────────────────────
    rag_chunk_size: int = Field(default=800, env="RAG_CHUNK_SIZE")
    rag_chunk_overlap: int = Field(default=100, env="RAG_CHUNK_OVERLAP")
    rag_top_k: int = Field(default=5, env="RAG_TOP_K")
    rag_score_threshold: float = Field(default=0.3, env="RAG_SCORE_THRESHOLD")
    rag_db_path: str = Field(default="./rag.db", env="RAG_DB_PATH")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
