"""Constants for integration_sgy."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "integration_sgy"
CONF_API_BASE = "api_base"
CONF_COOKIES = "cookies"
CONF_UPDATE_INTERVAL = "update_interval"
DEFAULT_API_BASE = "x.schoology.com"
DEFAULT_UPDATE_INTERVAL = 60  # minutes
ATTRIBUTION = "Data provided by Schoology"
