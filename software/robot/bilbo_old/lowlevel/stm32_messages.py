import ctypes
from utils.callbacks import Callback
from utils.ctypes_utils import STRUCTURE
from utils.logging_utils import Logger
from bilbo_old.lowlevel.stm32_errors import TWIPR_SupervisorErrorCodes, TWIPR_ErrorCode
from core.communication.serial.serial_interface import SerialCommandType

supervisor_logger = Logger('supervisor')
supervisor_logger.setLevel('INFO')


# ======================================================================================================================
# INCOMING MESSAGES
# ======================================================================================================================
# Events
# ======================================================================================================================
TWIPR_MESSAGE_PRINT_WARNING = 0x0301

class TWIPR_WarningMessage:
    @classmethod
    def printWarningMessage(cls, message, *args, **kwargs):
        supervisor_logger.warning(f"{TWIPR_ErrorCode(message.data['error']).name}: ID {TWIPR_SupervisorErrorCodes(message.data['id']).name}: {message.data['text'].decode('utf-8')}")

    command: SerialCommandType = SerialCommandType.UART_CMD_EVENT
    address: int = TWIPR_MESSAGE_PRINT_WARNING
    callback: Callback = printWarningMessage

    class data_type(ctypes.Structure):
        _fields_ = [("id", ctypes.c_uint8), ("error", ctypes.c_uint8), ("text", ctypes.c_char*50), ]


BILBO_LL_MESSAGE_DEBUG_ADDRESS = 0x0011



# ======================================================================================================================
class BILBO_LL_Message_Debug:
    command = SerialCommandType.UART_CMD_EVENT
    address = BILBO_LL_MESSAGE_DEBUG_ADDRESS

    @STRUCTURE
    class data_type:
        # noinspection PyTypeChecker
        FIELDS = {
            'flags': ctypes.c_uint8,
            'data': ctypes.c_char * 100
        }

    @classmethod
    def printDebugMessage(cls, message, *args, **kwargs):
        ...
# ======================================================================================================================