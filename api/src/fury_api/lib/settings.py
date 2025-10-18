import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Literal

from dotenv import load_dotenv
from pydantic import BaseConfig, BaseSettings, Extra, SecretStr, ValidationError, root_validator

__all__ = [
    "ServerSettings",
    "AppSettings",
    "APISettings",
    "DevExSettings",
    "LoggingSettings",
    "DatabaseSettings",
    "OpenAPISettings",
    "SettingsConfig",
    "ExperimentalSettings",
    "load_settings",
    "config",
    "version",
    "BASE_DIR",
]

module_name, *_ = __package__.split(".", maxsplit=1)
version = importlib.import_module(module_name).__version__
BASE_DIR: Path = Path(importlib.import_module(module_name).__file__).parent


class RootConfig(BaseConfig):
    env_prefix: str = "FURY_API_"
    env_file: str | None = ".env"
    env_file_encoding: str = "utf-8"
    validate_all: bool = True
    case_sensitive: bool = False
    extra: Extra = Extra.ignore


class ServerSettings(BaseSettings):
    """Server configuration."""

    class Config(RootConfig):  # noqa: D106
        env_prefix = "FURY_API_SERVER_"

    APP_PATH: str = "fury_api.main:app"
    HOST: str = "localhost"
    PORT: int = 3000
    KEEPALIVE: int = 65
    RELOAD: bool = False
    RELOAD_DIRS: ClassVar[list[str]] = [f"{BASE_DIR}"]
    WORKERS: int = 1
    PROFILING_ENABLED: bool = False


class AppSettings(BaseSettings):
    """Application settings."""

    class Config(RootConfig):  # noqa: D106
        env_prefix = "FURY_API_APP_"

    DEBUG: bool = True
    ENVIRONMENT: str = "dev"
    NAME: str = "Fury API"
    SLUG: str = "fury_api"
    VERSION: str = version

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "prod"

    @property
    def is_testing(self) -> bool:
        return self.ENVIRONMENT == "test"

    @property
    def is_local(self) -> bool:
        return self.ENVIRONMENT == "local"


class APISettings(BaseSettings):
    """API settings."""

    class Config(RootConfig):  # noqa: D106
        env_prefix = "FURY_API_"

    CORS_ORIGINS: ClassVar[list[str]] = ["*"]
    CORS_METHODS: ClassVar[list[str]] = ["*"]
    CORS_HEADERS: ClassVar[list[str]] = ["Authorization", "Content-Type"]

    # This must be a Fernet key must be 32 url-safe base64-encoded bytes. Fernet.generate_key()
    SECRET_KEY: str = "V3KihWm1MLiZPpVrbhBXiGtHEitE6fB9gIzxM3VcPaw="

    AUTH_TOKEN_HEADER: str = "API-Key"
    AUTH_TOKEN_SECRET: SecretStr = "example-secret-key"  # TODO: I don't think this is being used for anything? Maybe with the admin domain we no longer need this.

    LONG_LIVED_TOKEN_ALGORITHM: str = "HS256"
    LONG_LIVED_TOKEN_KEY: SecretStr = "suMCrCpbI69GVODCkHvHNA=="  # TODO: On Project Setup this should be generated to avoid using the same key for all projects
    LONG_LIVED_TOKEN_EXPIRY: int = 60 * 60 * 24 * 30 * 12 * 10  # 10 years

    AUTH_HEADER: str = "Authorization"
    AUTH_SCHEME: str = "bearer"

    AUTH_TOKEN_CUSTOM_TRANSLATION: ClassVar[dict[str, str]] = {
        "user_id": "firebase_id",
        "name": "name",
        "email": "email",
    }

    SERVICES_AUTOCOMMIT: bool = True

    AUTH_ALGORITHM: str = "RS256"
    AUTH_ISSUER: str = "local"
    AUTH_DOMAIN: (
        str | None
    )  # Not being  used right now, only needed in the future if we want to support multiple issuers.

    ADMIN_TOKEN: SecretStr | None


class DevExSettings(BaseSettings):
    """Dev settings."""

    class Config(RootConfig):  # noqa: D106
        env_prefix = "FURY_API_DEVEX_"

    ENABLED: bool = False

    ALLOW_ANY_AUTH_TOKEN_FOR_NEW_ORGANIZATION: bool = True

    AUTH_OVERRIDE_ENABLED: bool = True
    AUTH_OVERRIDE_ORGANIZATION_ID: int | None = None
    AUTH_OVERRIDE_USER_ID: int | None = None
    AUTH_OVERRIDE_USER_NAME: str | None = None
    AUTH_OVERRIDE_USER_EMAIL: str | None = None
    AUTH_OVERRIDE_FIREBASE_USER_ID: str | None = None

    TOKEN_GENERATION_FIREBASE_USER_ID: str | None

    @root_validator
    def disable_all_if_disabled(cls, values: dict[str, Any]) -> dict[str, Any]:
        if not values["ENABLED"]:
            for key in cls.__fields__:
                if key != "ENABLED":
                    if cls.__fields__[key].type_ == bool:  # noqa: E721
                        values[key] = False
                    else:
                        values[key] = None
        return values


class LoggingSettings(BaseSettings):
    """Logging settings."""

    class Config(RootConfig):  # noqa: D106
        env_prefix = "FURY_API_LOGGING_"

    LEVEL: str = "INFO"
    FORMAT: Literal["json", "console"] = "console"

    FORMAT_EXTERNAL: str = "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)s | %(message)s"


class DatabaseSettings(BaseSettings):
    """Database settings."""

    class Config(RootConfig):  # noqa: D106
        env_prefix = "FURY_DB_"

    ECHO: bool = False
    ECHO_POOL: bool = False

    POOL_DISABLED: bool = False
    POOL_MAX_OVERFLOW: int = 10
    POOL_SIZE: int = 10
    POOL_TIMEOUT: int = 30
    POOL_PRE_PING: bool = True

    CONNECT_ARGS: ClassVar[dict[str, str]] = {}

    URL: str | None = None
    ENGINE: str = "postgresql+psycopg"
    USER: str = "postgres"
    PASSWORD: SecretStr = "postgres"
    HOST: str = "127.0.0.1"
    PORT: int = 5432
    NAME: str = "beyond-gravity-local"

    SCHEMA: str = "platform"

    READ_ONLY_URL: str | None = None
    FORCE_READ_ONLY: bool = False

    TENANT_ROLE_ENABLED: bool = True
    TENANT_ROLE: str = "tenant_user"
    TENANT_ROLE_RO: str = "tenant_user_ro"
    TENANT_PARAMETER: str = "app.current_organization_id"
    TENANT_QUERY_ROLE_RO: str = "tenant_query_ro"

    NAMING_CONVENTION: ClassVar[dict[str, str]] = {
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }

    @root_validator(pre=False)
    def assemble_url(cls, values: dict[str, Any]) -> dict[str, Any]:
        url = values.get("URL")
        if url is not None:
            return values
        values["URL"] = (
            f"{values['ENGINE']}://{values['USER']}:{values['PASSWORD'].get_secret_value()}@"
            f"{values['HOST']}:{values['PORT']}/{values['NAME']}"
        )
        return values


class OpenAPISettings(BaseSettings):
    """OpenAPI settings."""

    class Config(RootConfig):  # noqa: D106
        env_prefix = "FURY_API_OPENAPI_"

    CONTACT_NAME: str = "Andre Cavalheiro"
    CONTACT_EMAIL: str = "andre.cavalheiro13@gmail.com"
    TITLE: str | None = "Fury API"
    VERSION: str = f"v{version}"
    DESCRIPTION: str = "Fury API is a REST API for several projects by Cavalheiro"
    SCHEMA_PATH: str = "/api/schema"


class FirebaseSettings(BaseSettings):
    """Firebase settings."""

    class Config(RootConfig):  # noqa: D106
        env_prefix = "FURY_FIREBASE_"

    PROJECT_ID: SecretStr
    PRIVATE_KEY_ID: SecretStr
    PRIVATE_KEY: SecretStr
    CLIENT_EMAIL: SecretStr
    CLIENT_ID: SecretStr
    AUTH_URI: str = "https://accounts.google.com/o/oauth2/auth"
    TOKEN_URI: str = "https://oauth2.googleapis.com/token"
    AUTH_PROVIDER_X509_CERT_URL: str = "https://www.googleapis.com/oauth2/v1/certs"
    CLIENT_X509_CERT_URL: SecretStr
    UNIVERSE_DOMAIN: str = "googleapis.com"
    WEB_API_KEY: SecretStr


class ExperimentalSettings(BaseSettings):
    """Experimental settings."""

    class Config(RootConfig):  # noqa: D106
        env_prefix = "FURY_API_EXPERIMENTAL_"


@dataclass(frozen=True, kw_only=True, slots=True)
class SettingsConfig:
    server: ServerSettings
    app: AppSettings
    api: APISettings
    dev: DevExSettings
    logging: LoggingSettings
    database: DatabaseSettings
    openapi: OpenAPISettings
    firebase: FirebaseSettings
    experimental: ExperimentalSettings


_loaded_settings: SettingsConfig | None = None


def load_settings(force_reload: bool = False) -> SettingsConfig:
    global _loaded_settings
    if _loaded_settings is not None and not force_reload:
        return _loaded_settings

    load_dotenv()
    try:
        _loaded_settings = SettingsConfig(
            server=ServerSettings(),
            app=AppSettings(),
            api=APISettings(),
            dev=DevExSettings(),
            logging=LoggingSettings(),
            database=DatabaseSettings(),
            openapi=OpenAPISettings(),
            firebase=FirebaseSettings(),
            experimental=ExperimentalSettings(),
        )
    except ValidationError as exc:
        print(f"Error loading settings: {exc}")
        raise

    return _loaded_settings


config = load_settings()
