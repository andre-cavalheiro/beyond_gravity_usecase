from fury_api.lib.repository import GenericSqlExtendedRepository
from .models import Earthquake

__all__ = ["EarthquakeRepository"]


class EarthquakeRepository(GenericSqlExtendedRepository[Earthquake]):
    def __init__(self) -> None:
        super().__init__(model_cls=Earthquake)
