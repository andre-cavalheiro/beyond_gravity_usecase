import importlib
from enum import Enum
from typing import Any, ClassVar, NamedTuple, TYPE_CHECKING

from fury_api.core.service import SqlService
from fury_api.core.unit_of_work import UnitOfWork
from fury_api.lib.settings import config
from fury_api.lib.utils.string import snake_case_to_pascal


if TYPE_CHECKING:
    from fury_api.domain.users.models import User


class ServiceType(Enum):
    USERS = "users"
    PLUGINS = "plugins"
    EARTHQUAKES = "earthquakes"
    IMAGE_TRANSFORMATIONS = "image_transformations"


ServiceDependency = NamedTuple("ServiceDependency", [("service_type", ServiceType), ("kwargs", dict[str, Any])])

ServiceConfig = NamedTuple(
    "ServiceConfig",
    [
        ("domain", str),
        ("class_name", str),
        ("dependencies", dict[str, ServiceDependency]),
    ],
)


class ServiceFactory:
    # Useful in edge cases to side-pass standard nomenclature (see self._get_config)
    _service_configs: ClassVar[dict[ServiceType, ServiceConfig]] = {}

    @staticmethod
    def _get_service_class(domain: str, class_name: str) -> type[SqlService]:
        """
        Dynamically import and return the service class.

        Args:
            class_name (str): The name of the service class.

        Returns:
            Type[SqlService]: The service class.

        Raises:
            ImportError: If the class cannot be imported.
        """
        module_name = f"{config.app.SLUG}.domain.{domain}.services"
        try:
            module = importlib.import_module(module_name)
            return getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Could not import class {class_name} from module {module_name}") from e

    @classmethod
    def _get_config(cls, service_type: ServiceType) -> ServiceConfig:
        config = cls._service_configs.get(service_type)

        if config is None:
            # Default config
            config = ServiceConfig(
                domain=service_type.value,
                class_name=f"{snake_case_to_pascal(service_type.value)}Service",
                dependencies={},
            )

        return config

    @classmethod
    def create_service(
        cls,
        service_type: ServiceType,
        uow: UnitOfWork,
        *,
        auth_user: "User | None" = None,
        **kwargs: Any,
    ) -> SqlService:
        """
        Create a service based on the given service type.

        Args:
            service_type (ServiceType): The type of service to create.
            uow (UnitOfWork): Unit of work instance.
            auth_user (User | None): Authenticated user, if any.
            vault_client (VaultClient | None): Vault client, if any.
            use_background_tasks (bool): Whether to use background tasks.
            **kwargs (Any): Additional arguments for the service constructor.

        Returns:
            SqlService: The created service instance.

        Raises:
            ValueError: If the service type is unknown.
        """
        kwargs.update({"auth_user": auth_user})

        return cls._create_service(service_type, uow, **kwargs)

    @classmethod
    def _create_service(
        cls,
        service_type: ServiceType,
        uow: UnitOfWork,
        *,
        _created_services: dict[ServiceType, SqlService] | None = None,
        **kwargs: Any,
    ) -> SqlService:
        config = cls._get_config(service_type)
        if config is None:
            raise ValueError(f"Unknown service type: {service_type}")

        if _created_services is None:
            _created_services = {}

        if service_type in _created_services:
            return _created_services[service_type]

        service_class = cls._get_service_class(config.domain, config.class_name)
        _created_services[service_type] = service_class.__new__(service_class)
        _created_services[service_type].__init__(
            uow,
            **kwargs,
            **(cls._create_dependencies(config.dependencies, uow, _created_services=_created_services, **kwargs)),
        )
        return _created_services[service_type]

    @classmethod
    def _create_dependencies(
        cls,
        dependencies: dict[str, ServiceDependency],
        uow: UnitOfWork,
        *,
        _created_services: dict[ServiceConfig, SqlService] | None = None,
        **kwargs: Any,
    ) -> dict[str, SqlService]:
        return {
            key: cls._create_service(
                dependency.service_type, uow, _created_services=_created_services, **{**kwargs, **dependency.kwargs}
            )
            for key, dependency in dependencies.items()
        }
