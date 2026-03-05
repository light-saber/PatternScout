from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./patternscout.db"

    GOOGLE_API_KEY: str = ""
    GOOGLE_CX: str = ""

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_VISION_MODEL: str = "qwen2.5-vl:latest"
    OLLAMA_TEXT_MODEL: str = "qwen3.5:latest"

    SCREENSHOTS_DIR: str = "./screenshots"
    API_V1_STR: str = "/api/v1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
