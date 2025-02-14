import dataclasses

from bilbo_old.communication.bilbo_communication import BILBO_Communication
from bilbo_old.lowlevel.stm32_sample import BILBO_LL_Sample


@dataclasses.dataclass
class TWIPR_Sensors_IMU:
    gyr: dict = dataclasses.field(default_factory=lambda: {'x': 0.0, 'y': 0.0, 'z': 0.0})
    acc: dict = dataclasses.field(default_factory=lambda: {'x': 0.0, 'y': 0.0, 'z': 0.0})


@dataclasses.dataclass
class TWIPR_Sensors_Power:
    bat_voltage: float = 0.0
    bat_current: float = 0.0


@dataclasses.dataclass
class TWIPR_Sensors_Drive_Data:
    speed: float = 0.0
    torque: float = 0.0
    slip: bool = False


@dataclasses.dataclass
class TWIPR_Sensors_Drive:
    left: TWIPR_Sensors_Drive_Data = dataclasses.field(default_factory=TWIPR_Sensors_Drive_Data)
    right: TWIPR_Sensors_Drive_Data = dataclasses.field(default_factory=TWIPR_Sensors_Drive_Data)


@dataclasses.dataclass
class TWIPR_Sensors_Distance:
    front: float = 0.0
    back: float = 0.0


@dataclasses.dataclass
class TWIPR_Sensors_Sample:
    imu: TWIPR_Sensors_IMU = dataclasses.field(default_factory=TWIPR_Sensors_IMU)
    power: TWIPR_Sensors_Power = dataclasses.field(default_factory=TWIPR_Sensors_Power)
    drive: TWIPR_Sensors_Drive = dataclasses.field(default_factory=TWIPR_Sensors_Drive)
    distance: TWIPR_Sensors_Distance = dataclasses.field(default_factory=TWIPR_Sensors_Distance)


class TWIPR_Sensors:
    _comm: BILBO_Communication

    imu: TWIPR_Sensors_IMU
    power: TWIPR_Sensors_Power
    drive: TWIPR_Sensors_Drive
    distance: TWIPR_Sensors_Distance

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self, comm: BILBO_Communication):
        self._comm = comm
        self._comm.callbacks.rx_stm32_sample.register(self._onSample)

        self.imu = TWIPR_Sensors_IMU(gyr={'x':0, 'y': 0, 'z': 0}, acc={'x':0, 'y': 0, 'z': 0})
        self.power = TWIPR_Sensors_Power(bat_voltage=0, bat_current=0)
        self.drive = TWIPR_Sensors_Drive()
        self.distance = TWIPR_Sensors_Distance()

    # ------------------------------------------------------------------------------------------------------------------
    def init(self):
        ...

    def start(self):
        ...
    # ------------------------------------------------------------------------------------------------------------------
    def getSample(self):
        sample = TWIPR_Sensors_Sample()
        sample.imu = self.imu
        sample.drive = self.drive
        sample.power.bat_voltage = self.power.bat_voltage
        return sample

    # ------------------------------------------------------------------------------------------------------------------
    def _onSample(self, sample: BILBO_LL_Sample, *args, **kwargs):
        self.imu.gyr = dataclasses.asdict(sample.sensors.gyr)
        self.imu.acc = dataclasses.asdict(sample.sensors.acc)
        self.drive.left.speed = sample.sensors.speed_left
        self.drive.right.speed = sample.sensors.speed_right
        self.power.bat_voltage = sample.sensors.battery_voltage
        self.power.bat_current = 0
        self.distance.front = 0
        self.distance.back = 0

    # ------------------------------------------------------------------------------------------------------------------
    def _readImu(self):
        ...

    # ------------------------------------------------------------------------------------------------------------------
    def _readPower(self):
        ...

    # ------------------------------------------------------------------------------------------------------------------
    def _readDrive(self):
        ...
