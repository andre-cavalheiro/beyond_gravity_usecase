__all__ = ["OrganizationsError", "OrganizationUserSecretAlreadyExistsError", "BlueprintNotFoundForDefaultEntityError"]


class OrganizationsError(Exception):
    pass


class OrganizationUserSecretAlreadyExistsError(OrganizationsError):
    def __init__(self, secret_name: str):
        super().__init__(f"User secret {secret_name} already exists")


class BlueprintNotFoundForDefaultEntityError(OrganizationsError):
    def __init__(self, entity_id: str, blueprint_id: str):
        super().__init__(f"Blueprint {blueprint_id} not found for default entity {entity_id}")
