"""
app/core/config.py
------------------
Central configuration loaded from environment variables.
Never hardcode secrets — always use .env
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- LLM ---
    groq_api_key: str = Field(default="", env="GROQ_API_KEY")
    gemini_api_key: str = Field(default="", env="GEMINI_API_KEY")
    openrouter_api_key: str = Field(default="", env="OPENROUTER_API_KEY")
    llm_provider: str = Field(default="groq", env="LLM_PROVIDER")
    llm_model: str = Field(default="llama-3.1-8b-instant", env="LLM_MODEL")
    llm_temperature: float = Field(default=0.0, env="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=1024, env="LLM_MAX_TOKENS")
    llm_timeout_seconds: int = Field(default=30, env="LLM_TIMEOUT_SECONDS")

    # --- Embeddings ---
    embedding_model: str = Field(default="all-MiniLM-L6-v2", env="EMBEDDING_MODEL")

    # --- Vector DB ---
    vectordb_path: str = Field(default="./data/vectordb", env="VECTORDB_PATH")
    collection_name: str = Field(default="policy_docs", env="COLLECTION_NAME")

    # --- RAG ---
    chunk_size: int = Field(default=512, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=50, env="CHUNK_OVERLAP")
    top_k_results: int = Field(default=5, env="TOP_K_RESULTS")

    # --- MCP Server ---
    mcp_host: str = Field(default="0.0.0.0", env="MCP_HOST")
    mcp_port: int = Field(default=8001, env="MCP_PORT")

    # --- App ---
    app_host: str = Field(default="0.0.0.0", env="APP_HOST")
    app_port: int = Field(default=8000, env="APP_PORT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # --- Evaluation Thresholds ---
    min_faithfulness_score: float = Field(default=0.75, env="MIN_FAITHFULNESS_SCORE")
    min_accuracy_score: float = Field(default=0.70, env="MIN_ACCURACY_SCORE")

    # --- Security / Guardrails ---
    max_steps_per_query: int = Field(default=10, env="MAX_STEPS_PER_QUERY")
    request_timeout_seconds: int = Field(default=60, env="REQUEST_TIMEOUT_SECONDS")
    max_retries: int = Field(default=3, env="MAX_RETRIES")

    # --- Paths ---
    data_dir: Path = Path("./data")
    pdfs_dir: Path = Path("./data/pdfs")
    logs_dir: Path = Path("./logs")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
