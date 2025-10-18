__all__ = ["UserError", "UserNoSystemAccessError"]


class UserError(Exception):
    pass


class UserNoSystemAccessError(UserError):
    def __init__(self) -> None:
        super().__init__("Only users with system access can create system users")
