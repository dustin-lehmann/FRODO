import ctypes
import enum

from utils.ctypes_utils import STRUCTURE


# Structures
@STRUCTURE
class twipr_control_external_input:
    FIELDS = [("u_direct_1", ctypes.c_float),
                ("u_direct_2", ctypes.c_float),
                ("u_balancing_1", ctypes.c_float),
                ('u_balancing_2', ctypes.c_float),
                ("u_velocity_forward", ctypes.c_float),
                ("u_velocity_turn", ctypes.c_float)]



class twipr_control_direct_input(ctypes.Structure):
    _fields_ = [("u_left", ctypes.c_float),
                ("u_right", ctypes.c_float), ]


class twipr_control_balancing_input(ctypes.Structure):
    _fields_ = [("u_left", ctypes.c_float),
                ("u_right", ctypes.c_float), ]

class twipr_control_speed_input(ctypes.Structure):
    _fields_ = [("forward", ctypes.c_float),
                ("turn", ctypes.c_float), ]

class TWIPR_Control_Status_LL(enum.IntEnum):
    TWIPR_CONTROL_STATE_LL_ERROR = 0
    TWIPR_CONTROL_STATE_LL_NORMAL = 1

class TWIPR_Control_Mode_LL(enum.IntEnum):
    TWIPR_CONTROL_MODE_LL_OFF = 0,
    TWIPR_CONTROL_MODE_LL_DIRECT = 1,
    TWIPR_CONTROL_MODE_LL_BALANCING = 2,
    TWIPR_CONTROL_MODE_LL_VELOCITY = 3

@STRUCTURE
class twipr_control_configuration_ll:
    FIELDS = {
        'K': ctypes.c_float*8,
        'forward_p': ctypes.c_float,
        'forward_i': ctypes.c_float,
        'forward_d': ctypes.c_float,
        'turn_p': ctypes.c_float,
        'turn_i': ctypes.c_float,
        'turn_d': ctypes.c_float,
    }