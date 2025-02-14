import dataclasses

# === OWN PACKAGES =====================================================================================================
from bilbo_old.control.bilbo_control import TWIPR_Control_Sample
from bilbo_old.estimation.twipr_estimation import TWIPR_Estimation_Sample
from bilbo_old.drive.twipr_drive import TWIPR_Drive_Sample
from bilbo_old.sensors.twipr_sensors import TWIPR_Sensors_Sample

# ======================================================================================================================
@dataclasses.dataclass
class BILBO_Sample_General:
    id: str = ''
    status: str = ''
    configuration: str = ''
    time: float = 0.0
    tick: int = 0
    sample_time: float = 0.0

# ======================================================================================================================
@dataclasses.dataclass
class BILBO_Sample:
    general: BILBO_Sample_General = dataclasses.field(default_factory=BILBO_Sample_General)
    control: TWIPR_Control_Sample = dataclasses.field(default_factory=TWIPR_Control_Sample)
    estimation: TWIPR_Estimation_Sample = dataclasses.field(default_factory=TWIPR_Estimation_Sample)
    drive: TWIPR_Drive_Sample = dataclasses.field(default_factory=TWIPR_Drive_Sample)
    sensors: TWIPR_Sensors_Sample = dataclasses.field(default_factory=TWIPR_Sensors_Sample)