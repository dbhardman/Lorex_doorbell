# Lorex doorbell for home assistant

Copied and modified from https://github.com/elad-bar/DahuaVTO2MQTT
Thanks to @elad-bar

Also copied and modifed from https://github.com/rroller/dahua
Thanks to @rroller

Provides for a camera, two binary sensors (motion and smart_motion), and sends an event to home assistant when the button is pressed.

There are two services, Enable and Disable which can be used for either the motion or smart motion.  This does not disable the Home Assistant entity but stops it from recieving messages from the doorbell.

The camera is derived from generic camera and has all the capabilities of the generic.

The event is stateless (ie the state of the event is the date and time).  The event has attribute event_type  which will be "pressed" or "idle".

Below is a yaml example of responding to a doorbell button press

alias: Front doorbell button pressed
description: Send a notification when the front doorbell is pressed
trigger:
  - platform: state
    entity_id:
      - event.doorbell
    from: null
    to: null
condition:
  - condition: template
    value_template: "{{state_attr(trigger.entity_id, 'event_type') == 'pressed'}}"
action:
  - service: camera.snapshot
    target:
      entity_id: camera.doorbell
    data:
      filename: /media/doorbell.jpg
  - delay:
      hours: 0
      minutes: 0
      seconds: 2
      milliseconds: 0
  - service: notify.notify
    data:
      message: Someone at front door
      data:
        image: /media/local/doorbell.jpg
mode: single




