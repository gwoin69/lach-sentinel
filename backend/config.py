from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    unraid_host: str = "192.168.111.253"
    unraid_api_port: int = 7443
    unraid_api_key: str = ""
    nmap_range: str = "192.168.111.0/24"
    nmap_interval: int = 3600
    metrics_interval: int = 60
    ws_push_interval: int = 5
    port: int = 8888
    tz: str = "Europe/Paris"
    database_url: str = "sqlite:////data/sentinel.db"
    testing: bool = False


settings = Settings()
