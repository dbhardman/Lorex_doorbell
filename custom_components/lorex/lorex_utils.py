"""Lorex utility functions and Enum classes."""

import socket

from .const import LorexType


def determine_type(host_ip) -> int:
    """Try different ports to determine lor_typ.

    port 5000 only open on doorbells.
    """
    lor_typ: int
    lor_typ = 0
    # creates a new socket
    s = socket.socket()
    try:
        # tries to connect to host using that port
        s.connect((host_ip, 5000))
        # make timeout if you want it a little faster ( less accuracy )
        # s.settimeout(0.2)
    except:
        # cannot connect, port is closed
        # return false
        lor_typ = 0
    else:
        # the connection was established, port is open!
        lor_typ = LorexType.DOORBELL
    if lor_typ:
        return lor_typ
    try:
        # tries to connect to host using that port
        s.connect(host_ip, 8086)
        # make timeout if you want it a little faster ( less accuracy )
        # s.settimeout(0.2)
    except:
        # cannot connect, port is closed
        # return false
        lor_typ = 0
    else:
        # the connection was established, port is open!
        lor_typ = LorexType.IPCAMERA
    if lor_typ:
        return lor_typ
    try:
        # tries to connect to host using that port
        s.connect((host_ip, 554))
        # make timeout if you want it a little faster ( less accuracy )
        # s.settimeout(0.2)
    except:
        # cannot connect, port is closed
        # return false
        lor_typ = 0
    else:
        # the connection was established, port is open!
        lor_typ = LorexType.DVR
    s.close()
    return lor_typ
