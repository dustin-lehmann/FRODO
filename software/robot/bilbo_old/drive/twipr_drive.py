import dataclasses
import enum

from bilbo_old.communication.bilbo_communication import BILBO_Communication
from bilbo_old.lowlevel.stm32_sample import BILBO_LL_Sample


class TWIPR_Drive_Status(enum.IntEnum):
    TWIPR_DRIVE_STATUS_OFF = 1,
    TWIPR_DRIVE_STATUS_ERROR = 0.
    TWIPR_DRIVE_STATUS_NORMAL = 2


@dataclasses.dataclass
class TWIPR_Drive_Data:
    status: TWIPR_Drive_Status = TWIPR_Drive_Status.TWIPR_DRIVE_STATUS_OFF
    torque: float = 0.0
    speed: float = 0.0
    input: float = 0.0


@dataclasses.dataclass
class TWIPR_Drive_Sample:
    left: TWIPR_Drive_Data = dataclasses.field(default_factory=TWIPR_Drive_Data)
    right: TWIPR_Drive_Data = dataclasses.field(default_factory=TWIPR_Drive_Data)


class TWIPR_Drive:
    _comm: BILBO_Communication
    left: TWIPR_Drive_Data
    right: TWIPR_Drive_Data

    def __init__(self, comm):
        self._comm = comm

        self.left = TWIPR_Drive_Data()
        self.right = TWIPR_Drive_Data()

        self._comm.callbacks.rx_stm32_sample.register(self._onSample)

    # ------------------------------------------------------------------------------------------------------------------
    def getSample(self) -> TWIPR_Drive_Sample:
        sample = TWIPR_Drive_Sample()
        sample.left = self.left
        sample.right = self.right
        return sample

    def _onSample(self, sample: BILBO_LL_Sample, *args, **kwargs):
        self.left.speed = sample.sensors.speed_left
        self.right.speed = sample.sensors.speed_right

    def _readDriveStatus(self):
        ...

    def _setTorque(self, torque: list):
        ...
