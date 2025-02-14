import dataclasses
import threading
import time

# === OWN PACKAGES =====================================================================================================
from control_board.control_board import RobotControl_Board
from control_board.stm32.stm32 import resetSTM32
from bilbo_old.utilities.id import readID
from utils.callbacks import callback_handler, CallbackContainer
from utils.events import EventListener, ConditionEvent, event_handler
from utils.exit import ExitHandler
from utils.singletonlock.singletonlock import SingletonLock, terminate
from bilbo_old.communication.bilbo_communication import BILBO_Communication
from bilbo_old.control.definitions import TWIPR_Control_Mode
from bilbo_old.control.bilbo_control import BILBO_Control
from bilbo_old.drive.twipr_drive import TWIPR_Drive
from bilbo_old.estimation.twipr_estimation import TWIPR_Estimation
from bilbo_old.logging.twipr_logging import TWIPR_Logging
from bilbo_old.logging.bilbo_sample import BILBO_Sample_General
from bilbo_old.sensors.twipr_sensors import TWIPR_Sensors
from utils.logging_utils import Logger, setLoggerLevel
from utils.time import IntervalTimer
from bilbo_old.supervisor.twipr_supervisor import TWIPR_Supervisor
from utils.revisions import get_versions, is_ll_version_compatible
from bilbo_old.utilities.buzzer import beep

# === GLOBAL VARIABLES =================================================================================================
logger = Logger("BILBO")
setLoggerLevel('wifi', 'DEBUG')


# === Callbacks ========================================================================================================
@callback_handler
class BILBO_Callbacks:
    update: CallbackContainer


# === Events ===========================================================================================================
@event_handler
class BILBO_Events:
    update: ConditionEvent


# ======================================================================================================================
class BILBO:
    id: str

    board: RobotControl_Board
    communication: BILBO_Communication
    control: BILBO_Control
    estimation: TWIPR_Estimation
    drive: TWIPR_Drive
    sensors: TWIPR_Sensors

    events: BILBO_Events

    supervisor: TWIPR_Supervisor
    lock: SingletonLock
    exit: ExitHandler

    loop_time: float

    _first_sample_user_message_sent: bool = False
    _eventListener: EventListener

    # _updateTimer: IntervalTimer = IntervalTimer(0.1)

    # === INIT =========================================================================================================
    def __init__(self, reset_stm32: bool = False):

        # terminate(lock_file="/tmp/twipr.lock")
        self.lock = SingletonLock(lock_file="/tmp/twipr.lock", timeout=10)
        self.lock.__enter__()

        if reset_stm32:
            logger.info(f"Reset STM32. This takes ~2 Seconds")
            resetSTM32()
            time.sleep(3)

        # Read the ID from the ID file
        self.id = readID()

        self.loop_time = 0
        # self._last_loop_time = 0

        # Set up the control board
        self.board = RobotControl_Board(device_class='robot_old', device_type='bilbo', device_revision='v4',
                                        device_id=self.id, device_name=self.id)

        # Start the communication module (WI-FI, Serial and SPI)
        self.communication = BILBO_Communication(board=self.board)

        # Set up the individual modules
        self.control = BILBO_Control(comm=self.communication)
        self.estimation = TWIPR_Estimation(comm=self.communication)
        self.drive = TWIPR_Drive(comm=self.communication)
        self.sensors = TWIPR_Sensors(comm=self.communication)
        self.supervisor = TWIPR_Supervisor(comm=self.communication)
        self.logging = TWIPR_Logging(comm=self.communication,
                                     control=self.control,
                                     estimation=self.estimation,
                                     drive=self.drive,
                                     sensors=self.sensors,
                                     general_sample_collect_function=self._getSample)

        self.communication.wifi.addCommand(identifier='beep',
                                           callback=beep,
                                           arguments=['frequency', 'time_ms', 'repeats'],
                                           description='Beeps')

        self.communication.wifi.addCommand(identifier='testfunction',
                                           callback=self.testfunction,
                                           arguments=['input1', 'input2'],
                                           description='Testfunction. Input1: float, Input2: string')

        self.events = BILBO_Events()
        self.callbacks = BILBO_Callbacks()
        self._eventListener = EventListener(event=self.communication.events.rx_stm32_sample, callback=self.update)
        self.exit = ExitHandler()
        self.exit.register(self._shutdown)

    # === METHODS ======================================================================================================
    def testfunction(self, input1: float, input2: str, *args, **kwargs):
        print(f"Testfunction called with inputs {input1} and {input2}")
        return {
            "output1": input1,
            "output2": input2,
        }
    # ------------------------------------------------------------------------------------------------------------------

    def init(self):
        self.board.init()
        self.communication.init()
        self.control.init()
        self.supervisor.init()
        self.sensors.init()
        self.logging.init()

    # ------------------------------------------------------------------------------------------------------------------
    def start(self):
        self.board.start()
        self.communication.start()

        # Read the firmware revision
        # if not self._checkFirmwareRevision():
        #     exit()

        success = self.control.start()

        if not success:
            logger.error("Cannot write control configuration. Exit program")
            exit()

        self.supervisor.start()
        self.sensors.start()
        self.logging.start()
        logger.info("Start BILBO")
        beep(frequency='middle', repeats=1)
        self._eventListener.start()
        self.board.setRGBLEDExtern([0, 0, 0])

    # ------------------------------------------------------------------------------------------------------------------
    def update(self):
        """
        This is the main update function for the robot_old
        """
        time_loop_start = time.perf_counter()
        # Update the control
        self.control.update()

        self._setExternalLEDs()

        # Update the logging
        self.logging.update()

        # Callbacks
        self.callbacks.update.call()

        # Events
        with self.events.update:
            self.events.update.notify_all()

        if not self._first_sample_user_message_sent:
            self._sendFirstSampleMessage()
        self.loop_time = time.perf_counter() - time_loop_start

    # === PRIVATE METHODS ==============================================================================================
    def _shutdown(self, *args, **kwargs):
        # Beep for audio reference
        beep(frequency='low', time_ms=200, repeats=2)
        logger.info("Shutdown BILBO")
        self.control.setMode(TWIPR_Control_Mode.TWIPR_CONTROL_MODE_OFF)
        self._eventListener.stop()
        self.lock.__exit__(None, None, None)
        time.sleep(1)
        self.board.setRGBLEDExtern([0, 0, 0])

        # Shutdown all modules
        # self.communication.close()

    # ------------------------------------------------------------------------------------------------------------------
    def _checkFirmwareRevision(self) -> bool:
        revision_stm32 = self.communication.serial.readFirmwareRevision()
        revision_data = get_versions()

        # Check if the LL firmware is compatible
        if revision_stm32 is None or not is_ll_version_compatible(current_ll_version=(revision_stm32['major'],
                                                                                      revision_stm32['minor']),
                                                                  min_ll_version=(
                                                                          revision_data['stm32_firmware']['major'],
                                                                          revision_data['stm32_firmware'][
                                                                              'minor'])):
            logger.error(
                f"STM32 Firmware not compatible. Current Version: {revision_stm32['major']}.{revision_stm32['minor']}."
                f" Required > {revision_data['stm32_firmware']['major']}.{revision_data['stm32_firmware']['minor']}")
            return False

        logger.info(
            f"Software Version {revision_data['software']['major']}.{revision_data['software']['minor']}"
            f" (STM32: {revision_stm32['major']}.{revision_stm32['minor']})")
        return True

    # ------------------------------------------------------------------------------------------------------------------
    def _getSample(self):
        sample = BILBO_Sample_General()
        sample.status = 'ok'
        sample.id = self.id
        sample.configuration = ''
        sample.time = self.communication.wifi.getTime()
        sample.tick = 0
        sample.sample_time = 0.1
        return sample

    # ------------------------------------------------------------------------------------------------------------------
    def _setExternalLEDs(self):
        if self.control.mode == TWIPR_Control_Mode.TWIPR_CONTROL_MODE_OFF:
            self.board.setRGBLEDExtern([2, 2, 2])
        elif self.control.mode == TWIPR_Control_Mode.TWIPR_CONTROL_MODE_BALANCING:
            self.board.setRGBLEDExtern([0, 10, 0])
        elif self.control.mode == TWIPR_Control_Mode.TWIPR_CONTROL_MODE_VELOCITY:
            self.board.setRGBLEDExtern([0, 0, 10])

    # ------------------------------------------------------------------------------------------------------------------
    def _sendFirstSampleMessage(self):
        logger.info(f"BILBO is running")
        logger.info(f"Battery Voltage: {self.logging.sample.sensors.power.bat_voltage:.2f} V")

        self._first_sample_user_message_sent = True

    # ------------------------------------------------------------------------------------------------------------------
    # def _threadFunction(self):
    #     self._updateTimer.reset()
    #     while True:
    #         self.update()
    #         self._updateTimer.sleep_until_next()

    # ------------------------------------------------------------------------------------------------------------------
    def __del__(self):
        if hasattr(self, 'lock'):
            self.lock.__exit__(None, None, None)
