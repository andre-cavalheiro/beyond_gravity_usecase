import datetime
import time
from dataclasses import dataclass
import httpx
from jose import JWSError, JWTError, jwt

from fury_api.lib import exceptions
from fury_api.lib.firebase import validate_token
from fury_api.lib.settings import config

__all__ = ["JWT"]


@dataclass(slots=True)
class JWT:
    token: str

    auth_algorithm: str = config.api.AUTH_ALGORITHM
    auth_issuer: str = config.api.AUTH_ISSUER
    auth_domain: str = config.api.AUTH_DOMAIN

    async def validate_user(self) -> dict:
        """
        Validates the firebase token and extracts the payload.

        Raises:
            exceptions.UnauthorizedError: If the token is invalid or cannot be verified.
        """
        try:
            return validate_token(self.token)

        except JWTError as e:
            raise exceptions.UnauthorizedError(detail=str(e)) from e
        except httpx.HTTPError as e:
            raise exceptions.UnauthorizedError(detail=str(e)) from e

    async def validate_system(self, key: str) -> dict:
        """
        Validates the system token and extracts the payload.

        Raises:
            exceptions.UnauthorizedError: If the token is invalid or cannot be verified.
        """
        try:
            return jwt.decode(
                token=self.token,
                key=key,
                algorithms=[self.auth_algorithm],
                issuer=self.auth_issuer,
                options={"verify_aud": False},
            )

        except JWTError as e:
            raise exceptions.UnauthorizedError(detail=str(e)) from e
        except httpx.HTTPError as e:
            raise exceptions.UnauthorizedError(detail=str(e)) from e

    @classmethod
    def create(cls, payload: dict, key: str, algorithm: str) -> str:
        try:
            expiry = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(
                seconds=config.api.LONG_LIVED_TOKEN_EXPIRY
            )
            payload["exp"] = int(time.mktime(expiry.timetuple()))
            payload["iat"] = int(time.mktime(datetime.datetime.now(tz=datetime.UTC).timetuple()))
            return jwt.encode(payload, key=key, algorithm=algorithm)
        except JWSError as e:
            raise e from e
