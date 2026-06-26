"""
Central configuration for the backend.

Every external API key is OPTIONAL. The app is designed to run fully
for free with zero keys configured:
  - No ANTHROPIC_API_KEY  -> falls back to a template-based script planner
  - No PEXELS_API_KEY     -> falls back to local placeholder/generated visuals
  - TTS (edge-tts / gTTS) -> free, no key needed
  - Captions (faster-whisper) -> free, runs locally, no key needed

Copy .env.example to .env and fill in keys only if you want the
upgraded behavior (smarter scripts, real stock footage).
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- General ---
    APP_NAME: str = "ReelForge AI Studio"
    ENV: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: str = "*"  # comma separated list in production

    # --- Storage ---
    STORAGE_DIR: str = "storage"
    MAX_UPLOAD_MB: int = 200

    # --- Optional: AI script planning ---
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"

    # --- Optional: stock footage / images ---
    PEXELS_API_KEY: str = ""
    PIXABAY_API_KEY: str = ""

    # --- Optional: paid text-to-video hook (disabled unless key present) ---
    TEXT_TO_VIDEO_PROVIDER: str = ""  # "runway" | "pika" | "stability" | ""
    TEXT_TO_VIDEO_API_KEY: str = ""

    # --- TTS ---
    DEFAULT_TTS_ENGINE: str = "edge-tts"  # "edge-tts" | "gtts"
    DEFAULT_VOICE: str = "en-US-AriaNeural"

    # --- Captions ---
    WHISPER_MODEL_SIZE: str = "base"  # tiny/base/small/medium - bigger = slower but more accurate
    WHISPER_DEVICE: str = "cpu"

    # --- Rendering ---
    MAX_CONCURRENT_RENDERS: int = 2
    RENDER_THREADS: int = 4
    DEFAULT_FPS: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
