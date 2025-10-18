from firebase_admin import auth, credentials, initialize_app

from fury_api.lib.exceptions import UnauthorizedError
from fury_api.lib.settings import config

__all__ = ["validate_token", "generate_custom_token"]


initialize_app(
    credential=credentials.Certificate(
        {
            "type": "service_account",
            "project_id": config.firebase.PROJECT_ID.get_secret_value(),
            "private_key_id": config.firebase.PRIVATE_KEY_ID.get_secret_value(),
            "private_key": config.firebase.PRIVATE_KEY.get_secret_value().replace("\\n", "\n"),
            "client_email": config.firebase.CLIENT_EMAIL.get_secret_value(),
            "client_id": config.firebase.CLIENT_ID.get_secret_value(),
            "auth_uri": config.firebase.AUTH_URI,
            "token_uri": config.firebase.TOKEN_URI,
            "auth_provider_x509_cert_url": config.firebase.AUTH_PROVIDER_X509_CERT_URL,
            "client_x509_cert_url": config.firebase.CLIENT_X509_CERT_URL.get_secret_value(),
            "universe_domain": config.firebase.UNIVERSE_DOMAIN,
        }
    ),
)


def validate_token(token: str) -> dict:
    """
    Validates the Firebase token and extracts the payload.

    Returns:
        dict: The payload of the decoded token. The structure of the returned dictionary is as follows:

        {
            'name': str,                         # User's full name (e.g., "André Cavalheiro").
            'picture': str,                      # URL to the user's profile picture (e.g., Google profile picture).
            'iss': str,                          # Issuer of the token (e.g., "https://securetoken.google.com/{project_id}").
            'aud': str,                          # Audience for the token (e.g., Firebase project ID).
            'auth_time': int,                    # Authentication time as a Unix timestamp.
            'user_id': str,                      # Firebase UID of the user (same as 'uid').
            'sub': str,                          # Subject identifier for the user (same as 'uid').
            'iat': int,                          # Issued-at time as a Unix timestamp.
            'exp': int,                          # Expiration time as a Unix timestamp.
            'email': str,                        # User's email address.
            'email_verified': bool,              # Whether the user's email is verified.
            'firebase': dict,                    # Additional Firebase-specific information:
                {
                    'identities': dict,          # Information about the user's linked identities (e.g., email, Google).
                    'sign_in_provider': str      # The provider used to sign in (e.g., "google.com").
                },
            'uid': str                           # Firebase UID of the user (same as 'user_id').
        }

    Raises:
        exceptions.UnauthorizedError: If the token is invalid or cannot be verified.
    """
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except auth.InvalidIdTokenError as e:
        raise UnauthorizedError(detail=str(e)) from e


def generate_custom_token(uid: str, additional_claims: dict | None = None):
    """
    Generate a custom token for the specified UID.

    :param uid: The firebase user ID for which to generate the token.
    :param additional_claims: Optional dictionary of custom fields to include in the token under the key "claims".
    :return: The generated custom token as a string.
    """
    try:
        custom_token = auth.create_custom_token(uid, additional_claims)
        return custom_token.decode("utf-8")
    except Exception as e:
        raise Exception(f"Error generating custom token: {e}")
