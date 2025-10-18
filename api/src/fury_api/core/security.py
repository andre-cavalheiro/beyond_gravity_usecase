from typing import Annotated, TYPE_CHECKING

from cryptography.fernet import Fernet
from fastapi import Depends, Request

from fury_api.lib.exceptions import UnauthorizedError
from fury_api.lib.jwt import JWT
from fury_api.lib.settings import config
from fury_common.utils.dicts import dict_renamer
from fury_api.core.factories import ServiceFactory, ServiceType, UnitOfWork, UnitOfWorkFactory
from fury_api.domain.users.services import UsersService

if TYPE_CHECKING:
    from fury_api.domain.users.models import User

__all__ = [
    "get_auth_token",
    "validate_token",
    "get_current_user",
    "get_current_user_new_organization",
    "validate_api_key",
    "encrypt_string",
    "decrypt_string",
]


def get_auth_token(request: Request) -> str:
    """Extracts the token from the request headers.

    Args:
        request (Request): The request object.

    Returns:
        str: The token.

    Raises:
        UnauthorizedError: If the token is not found or is invalid.
    """
    authorization = next((v for k, v in request.headers.items() if k.lower() == config.api.AUTH_HEADER.lower()), None)
    if not authorization:
        raise UnauthorizedError(detail="Missing token")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != config.api.AUTH_SCHEME:
            raise UnauthorizedError(detail="Invalid token scheme")
    except IndexError:
        raise UnauthorizedError(detail="Invalid token") from None
    else:
        return token


async def validate_token(token: Annotated[str, Depends(get_auth_token)]) -> dict:
    """Validates the token.

    Args:
        token (str): The token.
        uow (UnitOfWork): The uow.

    Returns:
        dict: The payload of the token.

    Raises:
        UnauthorizedError: If the token is invalid.
    """

    if config.dev.AUTH_OVERRIDE_ENABLED:
        return {
            "user_id": config.dev.AUTH_OVERRIDE_USER_ID,
            "name": config.dev.AUTH_OVERRIDE_USER_NAME,
            "email": config.dev.AUTH_OVERRIDE_USER_EMAIL,
        }

    try:
        # Normal User Validation (assuming firebase token)
        return await JWT(token).validate_user()
    except UnauthorizedError:
        try:
            # System User Validation (assuming system token)
            # TODO: Control ability to support this or not with ENV variable
            return await JWT(
                token, auth_algorithm=config.api.LONG_LIVED_TOKEN_ALGORITHM, auth_issuer="local"
            ).validate_system(key=config.api.LONG_LIVED_TOKEN_KEY.get_secret_value())
        except UnauthorizedError as e:
            raise e from e


async def get_user_from_token(token_payload: Annotated[dict, Depends(validate_token)]) -> "User":
    """Returns the current user.

    Args:
        token (dict): The token payload.

    Returns:
        User: The current user.

    Raises:
        UnauthorizedError: If the token is invalid.
    """
    from fury_api.domain.users.models import User as User

    claims = dict_renamer(token_payload, config.api.AUTH_TOKEN_CUSTOM_TRANSLATION, ignore_missing=True)
    user = User(**claims)
    if not user.name:
        user.name = user.email
    return user


async def get_current_user(
    current_user: Annotated["User", Depends(get_user_from_token)],
) -> "User":
    """Returns the current user.

    Args:
        current_user (User): The current user.

    Returns:
        User: The current user.

    Raises:
        UnauthorizedError: If the token is invalid.
    """

    if config.dev.AUTH_OVERRIDE_ENABLED:
        current_user.id = config.dev.AUTH_OVERRIDE_USER_ID
        current_user.organization_id = config.dev.AUTH_OVERRIDE_ORGANIZATION_ID
        # TODO: Would be cool to be able to mock the organization model within the user here too
        return current_user

    uow: UnitOfWork = UnitOfWorkFactory.get_uow(organization_id=current_user.organization_id)
    async with uow:
        users_service: UsersService = ServiceFactory.create_service(ServiceType.USERS, uow, has_system_access=True)
        existing_user = await users_service.get_user_by_email(current_user.email)
        if not existing_user.name:
            existing_user.name = existing_user.email

    if existing_user is None:
        raise UnauthorizedError(detail="Invalid token")
    return existing_user


async def get_current_user_new_organization(current_user: Annotated["User", Depends(get_user_from_token)]) -> "User":
    """Returns the current user if the token is valid for creating a new organization.

    Args:
        current_user (User): The current user.

    Returns:
        User: The current user.

    Raises:
        UnauthorizedError: If the token is invalid.
    """
    if current_user.id is not None or current_user.organization_id is not None:
        if config.dev.ALLOW_ANY_AUTH_TOKEN_FOR_NEW_ORGANIZATION:
            current_user.id = None
            current_user.firebase_id = None
            current_user.organization_id = None
        else:
            raise UnauthorizedError(detail="Invalid token")

    return current_user


async def validate_admin_token(token: Annotated[str, Depends(get_auth_token)]) -> dict:
    """Validates admin token to be ablet to execute admin domain endpoints.

    Args:
        token (str): The token.

    Returns:
        dict: The payload of the token.
    """
    if token != config.api.ADMIN_TOKEN.get_secret_value():
        raise UnauthorizedError(detail="Invalid token")


async def get_current_organization_id(current_user: Annotated["User", Depends(get_current_user)]) -> int:
    """Returns the current organization id.

    Args:
        current_user (User): The current user.

    Returns:
        int: The current organization id.

    Raises:
        UnauthorizedError: If the token is invalid.
    """
    if current_user.organization_id is None:
        raise UnauthorizedError(detail="Unable to retrieve organization ID from token")
    return current_user.organization_id


async def validate_api_key(request: Request) -> None:
    """Validates the API key.

    Args:
        request (Request): The request object.

    Raises:
        UnauthorizedError: If the API key is invalid.
    """
    api_key = next((v for k, v in request.headers.items() if k.lower() == config.api.AUTH_TOKEN_HEADER.lower()), None)
    if api_key is None:
        raise UnauthorizedError(detail="Missing API key")
    if api_key != config.api.AUTH_TOKEN_SECRET.get_secret_value():
        raise UnauthorizedError(detail="Invalid API key")


def create_long_lived_token(token_id: str, name: str, email: str) -> str:
    return JWT.create(
        {
            # These fields are present in standard firebase tokens
            "firebase_id": None,
            "name": name,
            "email": email,
            # These are custom to system tokens
            "id": token_id,  # This is not being used right now.
            "iss": "local",
            "sub": "system-user",
        },
        config.api.LONG_LIVED_TOKEN_KEY.get_secret_value(),
        algorithm=config.api.LONG_LIVED_TOKEN_ALGORITHM,
    )


async def encrypt_string(string: str) -> str:
    cipher_suite = Fernet(config.api.SECRET_KEY)
    return cipher_suite.encrypt(bytes(string, "utf-8")).decode()


async def decrypt_string(secret: str) -> str:
    cipher_suite = Fernet(config.api.SECRET_KEY)
    return cipher_suite.decrypt(secret).decode()
