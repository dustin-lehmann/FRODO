import ctypes

from utils.ctypes_utils import STRUCTURE

@STRUCTURE
class twipr_firmware_revision:
    FIELDS = {
        'major': ctypes.c_uint8,
        'minor': ctypes.c_uint8,
    }


