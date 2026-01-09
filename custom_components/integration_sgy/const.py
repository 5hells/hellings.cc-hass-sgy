"""Constants for integration_sgy."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "integration_sgy"
CONF_API_BASE = "api_base"
CONF_COOKIES = "cookies"
DEFAULT_API_BASE = "x.schoology.com"
ATTRIBUTION = "Data provided by Schoology"
