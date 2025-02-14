import dataclasses
from copy import copy

# === OWN PACKAGES =====================================================================================================
from bilbo_old.communication.bilbo_communication import BILBO_Communication
from bilbo_old.control.bilbo_control import BILBO_Control
from bilbo_old.drive.twipr_drive import TWIPR_Drive
from bilbo_old.estimation.twipr_estimation import TWIPR_Estimation
from bilbo_old.logging.bilbo_sample import BILBO_Sample
from bilbo_old.lowlevel.stm32_sample import BILBO_LL_Sample
from bilbo_old.sensors.twipr_sensors import TWIPR_Sensors
from utils.callbacks import callback_handler, CallbackContainer
from utils.events import EventListener
from utils.exit import ExitHandler
from utils.csv_utils import CSVLogger

# === Callbacks ========================================================================================================
@callback_handler
class TWIPR_Logging_Callbacks:
    on_sample: CallbackContainer

# === TWIPR Logging ====================================================================================================
class TWIPR_Logging:

    comm: BILBO_Communication
    control: BILBO_Control
    sensors: TWIPR_Sensors
    estimation: TWIPR_Estimation
    drive: TWIPR_Drive

    general_sample_collect_function: callable
    sample: BILBO_Sample
    sample_buffer: list[BILBO_Sample]

    _fileLogger: CSVLogger
    exit: ExitHandler

    _stm32_samples: list[BILBO_LL_Sample]
    _rx_stm32_event_listener: EventListener

    # === INIT =========================================================================================================
    def __init__(self, comm: BILBO_Communication,
                 control: BILBO_Control,
                 sensors: TWIPR_Sensors,
                 estimation: TWIPR_Estimation,
                 drive: TWIPR_Drive,
                 general_sample_collect_function: callable):

        self.comm = comm
        self.control = control
        self.sensors = sensors
        self.estimation = estimation
        self.drive = drive
        self.general_sample_collect_function = general_sample_collect_function

        # self.comm.spi.callbacks.rx_samples.register(self._stm32samples_callback)
        # self._rx_stm32_event_listener = EventListener(event=self.comm.events.rx_stm32_sample,
        #                                               callback=self._onEvent_rx_stm32_sample)

        self.sample_buffer = []
        self._stm32_samples = []

    # === METHODS ======================================================================================================
    def init(self) -> None:
        ...

    # ------------------------------------------------------------------------------------------------------------------
    def start(self) -> None:
        ...

    # ------------------------------------------------------------------------------------------------------------------
    def startFileLogging(self, filename, folder):
        ...

    def stopFileLogging(self):
        ...

    # ------------------------------------------------------------------------------------------------------------------
    def writeToFile(self, data, file, folder, header=None):
        logger = CSVLogger()
        logger.make_file(file, folder, header)
        logger.write_data(data)
        logger.close()

    # ------------------------------------------------------------------------------------------------------------------
    def update(self) -> None:
        # Collect the sample from all submodules
        sample = self._collectSample()
        sample_dict = dataclasses.asdict(sample)  # Type: Ignore

        # Send the current sample via WI-FI
        if self.comm.wifi.connected:
            self.comm.wifi.sendStream(sample_dict)


        # Log the sample
        self.sample = sample
    # ------------------------------------------------------------------------------------------------------------------


    # === PRIVATE METHODS ==============================================================================================
    def _collectSample(self) -> BILBO_Sample:
        sample = BILBO_Sample()

        sample.general = self.general_sample_collect_function()
        sample.control = self.control.getSample()
        sample.sensors = self.sensors.getSample()
        sample.estimation = self.estimation.getSample()
        sample.drive = self.drive.getSample()

        return sample

    def _stm32samples_callback(self, samples):
        self._stm32_samples = copy(samples)

    # def _onEvent_rx_stm32_sample(self, samples):
    #
    #     # 1. Send the sample to all modules
    #     self.control.
    #     ...