# Lorex doorbell for home assistant

Copied and modified from https://github.com/elad-bar/DahuaVTO2MQTT
Thanks to @elad-bar

Also copied and modifed from https://github.com/rroller/dahua
Thanks to @rroller

Provides for a camera.
Binary sensors for Motion, and Smart Human motion
A hass event for door bell button presses.

There are two services, Enable and Disable which can be used for either the motion or smart motion.  This does not disable the Home Assistant entity but stops it from recieving messages from the doorbell.

The camera is derived from generic camera and has all the capbilities of the generic.


