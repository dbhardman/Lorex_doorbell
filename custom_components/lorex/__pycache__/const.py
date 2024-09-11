"""Constants for the Lorex integration."""

from enum import Enum

DOMAIN = "lorex"
VERSION = "0.1.0"
ISSUE_URL = "https://github.com/dbhardman/Lorex_doorbell/issues"


# Device classes - https://www.home-assistant.io/integrations/binary_sensor/#device-class
"""MOTION_SENSOR_DEVICE_CLASS = "motion"
SAFETY_DEVICE_CLASS = "safety"
CONNECTIVITY_DEVICE_CLASS = "connectivity"
SOUND_DEVICE_CLASS = "sound"
DOOR_DEVICE_CLASS = "door"
DOORBELL_DEVICE_CLASS = "ding_dong"
"""

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
# CONF_PORT = "port"
# CONF_RTSP_PORT = "rtsp_port"

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
"""Event constants"""
# DOORBELL_MOTION = "db_motion"
# DOORBELL_SMART_MOTION = "db_smart_motion"
# DOORBELL_BUTTON_PRESS = "db_button_pressed"

"""Used in the config flow where we determine the type of device being connected"""
"""
LOREX_HANDLED_EVENTS = {
    "IntelliFrame",
    "VideoMotion",
    "AlarmLocal",
}
"""

"""these are all the events that we currently do NOT handle
LOREX_EVENTS = {
    "VideoMotionInfo",
    "LeFunctionStatusSync",
    "NewFile",
    "TimeChange",
    "BackKeyLight",
    "CrossRegionDetection",
    "AutoRegister",
    "RtspSessionDisconnect",
    "RtspSessionState",
    "NetAbort",
    "NTPAdjustTime",
    "PhoneCallDetect",
    "CallNoAnswered",
    "WlanWorkMode",
}
"""
