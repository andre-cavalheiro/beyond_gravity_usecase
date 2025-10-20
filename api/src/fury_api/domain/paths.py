API_ROOT = "/api/v1"

HEALTH_CHECK = "/health"
HEALTH_CHECK_VELINI = "/health/velini"

ORGANIZATIONS = "/organizations"
ORGANIZATIONS_SELF = f"{ORGANIZATIONS}/self"

USERS = "/users"
USERS_SELF = f"{USERS}/self"
USERS_ID = f"{USERS}/{{id_}}"

EARTHQUAKES = "/earthquakes"
EARTHQUAKES_ID = f"{EARTHQUAKES}/{{id_}}"
EARTHQUAKES_ID_IMAGE = f"{EARTHQUAKES}/{{id_}}/ciim_geo_heightmap"
EARTHQUAKES_INGEST = f"{EARTHQUAKES}/ingest"
