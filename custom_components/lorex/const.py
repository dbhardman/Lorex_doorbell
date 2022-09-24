"""Constants for the Lorex integration."""

DOMAIN = "lorex"
VERSION = "0.0.1"
ISSUE_URL = ""


# Device classes - https://www.home-assistant.io/integrations/binary_sensor/#device-class
MOTION_SENSOR_DEVICE_CLASS = "motion"
SAFETY_DEVICE_CLASS = "safety"
CONNECTIVITY_DEVICE_CLASS = "connectivity"
SOUND_DEVICE_CLASS = "sound"
DOOR_DEVICE_CLASS = "door"
DOORBELL_DEVICE_CLASS = "ding_dong"

# Platforms
BINARY_SENSOR = "binary_sensor"
SWITCH = "switch"
LIGHT = "light"
CAMERA = "camera"
SELECT = "select"
# right now for the lorex only using the camera and binary_sensor
PLATFORMS = [CAMERA, BINARY_SENSOR]


# Configuration and options
CONF_NAME = "name"
CONF_ENABLED = "enabled"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_PORT = "port"
CONF_RTSP_PORT = "rtsp_port"

# Defaults
DEFAULT_NAME = "Lorex"

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
This is a custom integration for {DOMAIN} doorbells
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""

# these are all the events that we currently do NOT handle
LOREX_EVENTS = {
    'VideoMotionInfo',
    'LeFunctionStatusSync',
    'IntelliFrame',
    'NewFile',
    'TimeChange',
    'BackKeyLight',
    'CrossRegionDetection',
    'AutoRegister',
    'RtspSessionDisconnect',
    'RtspSessionState',
    'NetAbort',
    'NTPAdjustTime',
    'PhoneCallDetect',
    'CallNoAnswered',
    'WlanWorkMode',
    'LorexConnected',

    }
