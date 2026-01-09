"""Constants for integration_blueprint."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "integration_blueprint"
CONF_API_BASE = "api_base"
CONF_COOKIES = "cookies"
DEFAULT_API_BASE = "x.schoology.com"
ATTRIBUTION = "Data provided by http://jsonplaceholder.typicode.com/"
