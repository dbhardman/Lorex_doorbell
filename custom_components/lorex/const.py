"""Constants for the Lorex integration."""

from enum import Enum

DOMAIN = "lorex"
VERSION = "0.1.0"
ISSUE_URL = "https://github.com/dbhardman/Lorex_doorbell/issues"


# Platforms
BINARY_SENSOR = "binary_sensor"
SWITCH = "switch"
LIGHT = "light"
CAMERA = "camera"
SELECT = "select"
EVENT = "event"
# currently used by lorex api
PLATFORMS = [BINARY_SENSOR, CAMERA, EVENT]


# Configuration and options
CONF_NAME = "name"
CONF_ENABLED = "enabled"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_PORT = "port"

# Defaults
DEFAULT_NAME = "Lorex"

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
This is a custom integration for {DOMAIN} doorbells
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""

"""Dauhua messages that the lorex system responds to.

"""
DAHUA_DEVICE_TYPE = "deviceType"
DAHUA_SERIAL_NUMBER = "serialNumber"
DAHUA_VERSION = "version"
DAHUA_BUILD_DATE = "buildDate"
DAHUA_CONSOLE_RUN_CMD = "console.runCmd"
DAHUA_GLOBAL_LOGIN = "global.login"
DAHUA_GLOBAL_KEEPALIVE = "global.keepAlive"
DAHUA_EVENT_MANAGER_ATTACH = "eventManager.attach"
DAHUA_CONFIG_MANAGER_GETCONFIG = "configManager.getConfig"
DAHUA_MAGICBOX_GETSOFTWAREVERSION = "magicBox.getSoftwareVersion"
DAHUA_MAGICBOX_GETDEVICETYPE = "magicBox.getDeviceType"
DAHUA_MAGICBOX_GETSYSINFO = "magicBox.getSysytemInfo"

DAHUA_ALLOWED_DETAILS = [DAHUA_DEVICE_TYPE, DAHUA_SERIAL_NUMBER]


# Lorextyps used in utils to determine the system
class LorexType(Enum):
    """Lorex device Type."""

    UNKNOWN = 0
    DOORBELL = 1
    IPCAMERA = 2
    PTZCAMERA = 3
    DVR = 4


# definitions for the event message
LOREX_MODEL = "lorexModel"
LOREX_ID = "lorexId"
LOREX_TIME_STAMP = "lorexTime"
INTELLIFRAME = "IntelliFrame"
VIDEOMOTION = "VideoMotion"
ALARMLOCAL = "AlarmLocal"
LOREX_CONNECTION = "lorex_Connection"
LOREX_CLIENT = "lorex_Client"
LOREX_GETTING_EVENTS = "lorex_events"
LOREX_DOORBELL_CODES = [ALARMLOCAL, INTELLIFRAME, VIDEOMOTION]


# doorbell event types used for event entity
LOREX_PRESSED = "pressed"
LOREX_IDLE = "idle"
