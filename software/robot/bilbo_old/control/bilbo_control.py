import copy
import dataclasses
import threading

from bilbo_old.lowlevel.stm32_sample import BILBO_LL_Sample
# === OWN PACKAGES =====================================================================================================
from utils.callbacks import Callback, callback_handler, CallbackContainer
from bilbo_old.communication.bilbo_communication import BILBO_Communication, BILBO_Communication_Callbacks
import bilbo_old.setup as settings
import bilbo_old.lowlevel.stm32_addresses as addresses
from bilbo_old.lowlevel.stm32_control import *
from utils.logging_utils import Logger
from bilbo_old.control.definitions import *
from utils.data import limit, are_lists_approximately_equal
from utils.time import IntervalTimer
from utils.delayed_executor import delayed_execution
import bilbo_old.control.config as control_config

# === Logger ===========================================================================================================
logger = Logger('control')
logger.setLevel('INFO')

# === BILBO Control Callbacks ==========================================================================================
@callback_handler
class BILBO_Control_Callbacks:
    mode_change: CallbackContainer  # Inputs: mode: BILBO_Control_Mode , forced_change: bool
    status_change: CallbackContainer  # Inputs: status: BILBO_Control_State, forced_change: bool
    error: CallbackContainer
    on_update: CallbackContainer

# === BILBO Control ====================================================================================================
class BILBO_Control:
    _comm: BILBO_Communication

    status: TWIPR_Control_Status
    mode: TWIPR_Control_Mode
    mode_ll: TWIPR_Control_Mode_LL
    status_ll: TWIPR_Control_Status_LL

    config: control_config.ControlConfig

    external_input: BILBO_Control_Input
    enable_external_input: bool
    input: BILBO_Control_Input

    callbacks: BILBO_Control_Callbacks


    _lastStm32Sample: BILBO_LL_Sample
    # _thread: threading.Thread
    _updateTimer: IntervalTimer = IntervalTimer(0.1)

    # === INIT =========================================================================================================
    def __init__(self, comm: BILBO_Communication):

        # Input Handling
        self._comm = comm

        # Load the default config
        self.config = None  # type: Ignore

        # Prepare the properties
        self.status = TWIPR_Control_Status(TWIPR_Control_Status.TWIPR_CONTROL_STATE_ERROR)
        self.mode = TWIPR_Control_Mode(TWIPR_Control_Mode.TWIPR_CONTROL_MODE_OFF)
        self.status_ll = TWIPR_Control_Status_LL(TWIPR_Control_Status_LL.TWIPR_CONTROL_STATE_LL_ERROR)
        self.mode_ll = TWIPR_Control_Mode_LL(TWIPR_Control_Mode_LL.TWIPR_CONTROL_MODE_LL_OFF)

        # self.input = TWIPR_ControlInput()
        self.external_input = BILBO_Control_Input()
        self.input = BILBO_Control_Input()
        self.enable_external_input = True

        # Register the STM32 Sample Receiving
        self._comm.callbacks.rx_stm32_sample.register(self._stm32Sample_callback)

        self.callbacks = BILBO_Control_Callbacks()

        # Add Commands to the WI-FI Module
        self._comm.wifi.addCommand(identifier='setControlMode',
                                   callback=self.setMode,
                                   arguments=['mode'],
                                   description='Sets the control mode')

        self._comm.wifi.addCommand(identifier='setNormalizedBalancingInput',
                                   callback=self.setNormalizedBalancingInput,
                                   arguments=['forward', 'turn'],
                                   description='Sets the Input')

        self._comm.wifi.addCommand(identifier='setSpeed',
                                   callback=self.setSpeed,
                                   arguments=['v', 'psi_dot'],
                                   description='Sets the Speed')

        # self._thread = threading.Thread(target=self._threadFunction)

        self._lastStm32Sample = None  # Type: Ignore

    # === METHODS ======================================================================================================
    def init(self):
        ...


    # ------------------------------------------------------------------------------------------------------------------
    def start(self):
        self.config = self.loadConfig('default')
        if self.config is None:
            return False
        # self._thread.start()
        return True

    # ------------------------------------------------------------------------------------------------------------------
    def update(self):
        # Step 1: Process the stm32 sample
        self._updateLLSample(self._lastStm32Sample)

        # Step 2: Process the external input
        external_input = self._updateExternalInput(self.external_input)

        # Step 3: Process the Input
        # TODO: For now, manual input is the only way to set the input, so we copy it for now
        self.input = external_input
        self._setInput(self.input)

        # Call user-defined update functions
        self.callbacks.on_update.call()

    # ------------------------------------------------------------------------------------------------------------------
    def loadConfig(self, name):
        logger.info(f"Load control config \"{name}\"...")
        config = control_config.load_config(name)
        if config is None:
            logger.warning(f"Control config \"{name}\" not found")
            return None

        success = self._writeControlConfig(config)
        if not success:
            logger.warning(f"Control config {name} failed")
            return None

        logger.info(f"Control config \"{name}\" loaded!")
        self._resetExternalInput()
        return config

    # ------------------------------------------------------------------------------------------------------------------
    def saveConfig(self, name, config=None):

        raise NotImplementedError

    # ------------------------------------------------------------------------------------------------------------------
    def setMode(self, mode: (int, TWIPR_Control_Mode)):

        # Check if the mode exists
        if isinstance(mode, int):
            try:
                mode = TWIPR_Control_Mode(mode)
            except ValueError:
                logger.warning(f"Value of {mode} is not a valid control mode")
                return

        if mode == self.mode:
            return

        logger.info(f"Setting control mode to {mode.name}")

        # Depending on the mode, set the lower level control mode
        if mode == TWIPR_Control_Mode.TWIPR_CONTROL_MODE_OFF:
            self._setControlMode_LL(TWIPR_Control_Mode_LL.TWIPR_CONTROL_MODE_LL_OFF)
        elif mode == TWIPR_Control_Mode.TWIPR_CONTROL_MODE_BALANCING:
            self._setControlMode_LL(TWIPR_Control_Mode_LL.TWIPR_CONTROL_MODE_LL_BALANCING)
        elif mode == TWIPR_Control_Mode.TWIPR_CONTROL_MODE_VELOCITY:
            self._setControlMode_LL(TWIPR_Control_Mode_LL.TWIPR_CONTROL_MODE_LL_VELOCITY)

        self._resetExternalInput()
        self.callbacks.mode_change.call(mode, forced_change=False)

    # ------------------------------------------------------------------------------------------------------------------
    def standUp(self):
        if not self.mode == TWIPR_Control_Mode.TWIPR_CONTROL_MODE_OFF:
            return
        self.setMode(TWIPR_Control_Mode.TWIPR_CONTROL_MODE_BALANCING)
        delayed_execution(self.setMode, 1, mode=TWIPR_Control_Mode.TWIPR_CONTROL_MODE_VELOCITY)

    # ------------------------------------------------------------------------------------------------------------------
    def fallOver(self, direction='forward'):
        if not self.mode == TWIPR_Control_Mode.TWIPR_CONTROL_MODE_VELOCITY:
            return

        if direction == 'forward':
            self.setSpeed(v=0.2, psi_dot=0)
        elif direction == 'backward':
            self.setSpeed(v=-0.2, psi_dot=0)
        else:
            raise Exception("Invalid direction")

        delayed_execution(self.setMode, 0.5, mode=TWIPR_Control_Mode.TWIPR_CONTROL_MODE_OFF)

    # ------------------------------------------------------------------------------------------------------------------
    def setNormalizedBalancingInput(self, forward: (int, float), turn: (int, float)):
        assert isinstance(forward, (int, float))
        assert isinstance(turn, (int, float))

        if self.mode == TWIPR_Control_Mode.TWIPR_CONTROL_MODE_BALANCING:
            forward_cmd_scaled = forward * self.config.manual.torque.forward_torque_gain
            turn_cmd_scaled = turn * self.config.manual.torque.turn_torque_gain
            torque_left = -(forward_cmd_scaled + turn_cmd_scaled)
            torque_right = -(forward_cmd_scaled - turn_cmd_scaled)

            self.external_input.balancing.u_left = torque_left + self.config.general.torque_offset[0]
            self.external_input.balancing.u_right = torque_right + self.config.general.torque_offset[1]

        else:
            ...


    # ------------------------------------------------------------------------------------------------------------------
    def setNormalizedSpeedInput(self, forward: (int, float), turn: (int, float)):
        assert isinstance(forward, (int, float))
        assert isinstance(turn, (int, float))

        if not -1 <= forward <= 1:
            logger.warning("Normalized forward speed must be between -1 and 1")
            return

        if not -1 <= turn <= 1:
            logger.warning("Normalized turn speed must be between -1 and 1")
            return

        if self.mode == TWIPR_Control_Mode.TWIPR_CONTROL_MODE_VELOCITY:
            forward_speed_scaled = forward * self.config.manual.velocity.forward_velocity_gain
            turn_speed_scaled = turn * self.config.manual.velocity.turn_velocity_gain
            self.external_input.velocity.forward = forward_speed_scaled
            self.external_input.velocity.turn = turn_speed_scaled
        else:
            ...


    # ------------------------------------------------------------------------------------------------------------------
    def setBalancingInput(self, u_left: float, u_right: float):
        assert isinstance(u_left, float)
        assert isinstance(u_right, float)

        if self.mode == TWIPR_Control_Mode.TWIPR_CONTROL_MODE_BALANCING:
            u_left = u_left + self.config.general.torque_offset[0]
            u_right = u_right + self.config.general.torque_offset[1]

            self.external_input.balancing.u_left = u_left
            self.external_input.balancing.u_right = u_right

    # ------------------------------------------------------------------------------------------------------------------
    def setSpeed(self, v: float = 0, psi_dot: float = 0):
        assert isinstance(v, (int, float))
        assert isinstance(psi_dot, (int, float))

        if self.mode == TWIPR_Control_Mode.TWIPR_CONTROL_MODE_VELOCITY:
            v = limit(v, self.config.manual.velocity.max_forward_velocity)
            psi_dot = limit(psi_dot, self.config.manual.velocity.max_turn_velocity)

            self.external_input.velocity.forward = v
            self.external_input.velocity.turn = psi_dot

    # ------------------------------------------------------------------------------------------------------------------
    def setStateFeedbackGain(self, K):
        logger.info(f"Set State Feedback Gain to {K}")
        self.config.statefeedback.gain = K
        self._setStateFeedbackGain_LL(K)

    # ------------------------------------------------------------------------------------------------------------------
    def setVelocityControlPID_Forward(self, P: float, I: float, D: float):
        logger.info(f"Set Velocity Control PID Forward to {P}, {I}, {D}")
        self.config.velocity_control.forward.feedback.Kp = P
        self.config.velocity_control.forward.feedback.Ki = I
        self.config.velocity_control.forward.feedback.Kd = D
        self._setVelocityControlPIDForward_LL(P, I, D)

    # ------------------------------------------------------------------------------------------------------------------
    def setVelocityControlPID_Turn(self, P: float, I: float, D: float):
        logger.info(f"Set Velocity Control PID Turn to {P}, {I}, {D}")
        self.config.velocity_control.turn.feedback.Kp = P
        self.config.velocity_control.turn.feedback.Ki = I
        self.config.velocity_control.turn.feedback.Kd = D
        self._setVelocityControlPIDTurn_LL(P, I, D)

    # ------------------------------------------------------------------------------------------------------------------
    def setVelocityController(self, config: TWIPR_Speed_Control_Config):
        raise NotImplementedError

    # ------------------------------------------------------------------------------------------------------------------
    def setMaxWheelSpeed(self, speed: (int, float)):
        logger.info(f"Set max wheel speed to {speed}")
        self.config.safety.max_speed = speed
        self._setMaxWheelSpeed_LL(speed)

    # ------------------------------------------------------------------------------------------------------------------
    def getSample(self) -> TWIPR_Control_Sample:
        sample = TWIPR_Control_Sample()
        sample.status = self.status
        sample.mode = self.mode
        sample.configuration = self.config.name
        sample.input = copy.copy(self.input)

        return sample

    # = PRIVATE METHODS ================================================================================================
    # def _threadFunction(self):
    #     self._updateTimer.reset()
    #     while True:
    #         self._update()
    #         self._updateTimer.sleep_until_next()

    # ------------------------------------------------------------------------------------------------------------------
    def _stm32Sample_callback(self, sample) -> None:
        self._lastStm32Sample = sample

    # ------------------------------------------------------------------------------------------------------------------
    def _writeControlConfig(self, config: control_config.ControlConfig):

        # Set statefeedback gain
        self._setStateFeedbackGain_LL(K=config.statefeedback.gain)

        # Set PID Control Values
        self._setVelocityControlPIDForward_LL(P=config.velocity_control.forward.feedback.Kp,
                                           I=config.velocity_control.forward.feedback.Ki,
                                           D=config.velocity_control.forward.feedback.Kd)

        self._setVelocityControlPIDTurn_LL(P=config.velocity_control.turn.feedback.Kp,
                                        I=config.velocity_control.turn.feedback.Ki,
                                        D=config.velocity_control.turn.feedback.Kd)

        # TODO Add Feedforward Values

        # TODO Set Safety Control Values
        self._setMaxWheelSpeed_LL(speed=config.safety.max_speed)

        # Check if the control is correctly set
        config_ll = self._readControlConfig_LL()

        if config_ll is None:
            return False

        if not are_lists_approximately_equal(config_ll['K'], config.statefeedback.gain):
            logger.warning("State Feedback Gain not set correctly")
            return False

        if not are_lists_approximately_equal(
                     [config.velocity_control.forward.feedback.Kp,
                            config.velocity_control.forward.feedback.Ki,
                            config.velocity_control.forward.feedback.Kd],
                     [config_ll['forward_p'], config_ll['forward_i'], config_ll['forward_d']]):
            logger.warning("PID Control Values not set correctly")
            return False

        if not are_lists_approximately_equal(
                     [config.velocity_control.turn.feedback.Kp,
                            config.velocity_control.turn.feedback.Ki,
                            config.velocity_control.turn.feedback.Kd],
                     [config_ll['turn_p'], config_ll['turn_i'], config_ll['turn_d']]):
            logger.warning("PID Control Values not set correctly")
            return False

        return True


    # ------------------------------------------------------------------------------------------------------------------
    def _setControlMode_LL(self, mode: TWIPR_Control_Mode_LL) -> None:

        assert (isinstance(mode, TWIPR_Control_Mode_LL))

        self._comm.serial.executeFunction(module=addresses.TWIPR_AddressTables.REGISTER_TABLE_GENERAL,
                                          address=addresses.TWIPR_ControlAddresses.ADDRESS_CONTROL_SET_MODE,
                                          data=mode.value,
                                          input_type=ctypes.c_uint8)

    # ------------------------------------------------------------------------------------------------------------------
    def _readControlMode_LL(self):
        ...

    # ------------------------------------------------------------------------------------------------------------------
    def _readControlState_LL(self):
        ...

    # ------------------------------------------------------------------------------------------------------------------
    def _setMaxWheelSpeed_LL(self, speed: (int, float)):
        self._comm.serial.writeValue(module=addresses.TWIPR_AddressTables.REGISTER_TABLE_GENERAL,
                                     address=addresses.TWIPR_ControlAddresses.ADDRESS_CONTROL_RW_MAX_WHEEL_SPEED,
                                     value=float(speed),
                                     type=ctypes.c_float)

    # ------------------------------------------------------------------------------------------------------------------
    def _setStateFeedbackGain_LL(self, K) -> None:
        assert (isinstance(K, list))
        assert (len(K) == 8)
        assert (all(isinstance(elem, (float, int)) for elem in K))

        self._comm.serial.executeFunction(module=addresses.TWIPR_AddressTables.REGISTER_TABLE_GENERAL,
                                          address=addresses.TWIPR_ControlAddresses.ADDRESS_CONTROL_SET_K,
                                          data=K,
                                          input_type=ctypes.c_float * 8,  # type: Ignore
                                          output_type=None)

    # ------------------------------------------------------------------------------------------------------------------
    def _setVelocityControlPIDForward_LL(self, P: float, I: float, D: float) -> None:
        self._comm.serial.executeFunction(module=addresses.TWIPR_AddressTables.REGISTER_TABLE_GENERAL,
                                          address=addresses.TWIPR_ControlAddresses.ADDRESS_CONTROL_SET_FORWARD_PID,
                                          data=[P, I, D],
                                          input_type=ctypes.c_float * 3, # type: Ignore
                                          output_type=None)

    # ------------------------------------------------------------------------------------------------------------------
    def _setVelocityControlPIDTurn_LL(self, P: float, I: float, D: float) -> None:
        self._comm.serial.executeFunction(module=addresses.TWIPR_AddressTables.REGISTER_TABLE_GENERAL,
                                          address=addresses.TWIPR_ControlAddresses.ADDRESS_CONTROL_SET_TURN_PID,
                                          data=[P, I, D],
                                          input_type=ctypes.c_float * 3, # type: Ignore
                                          output_type=None)

    # ------------------------------------------------------------------------------------------------------------------
    def _setVelocityControl_LL(self):
        raise NotImplementedError

    # ------------------------------------------------------------------------------------------------------------------
    def _setBalancingInput_LL(self, u_left: float, u_right: float):
        assert (isinstance(u_left, float))
        assert (isinstance(u_right, float))

        data = {
            'u_left': u_left,
            'u_right': u_right
        }

        self._comm.serial.executeFunction(module=addresses.TWIPR_AddressTables.REGISTER_TABLE_GENERAL,
                                          address=addresses.TWIPR_ControlAddresses.ADDRESS_CONTROL_SET_BALANCING_INPUT,
                                          data=data,
                                          input_type=twipr_control_balancing_input)

    # ------------------------------------------------------------------------------------------------------------------
    def _setSpeedInput_LL(self, v: float, psi_dot: float) -> None:
        assert (isinstance(v, (int, float)))
        assert (isinstance(psi_dot, (int, float)))

        data = {
            'forward': v,
            'turn': psi_dot
        }

        self._comm.serial.executeFunction(module=addresses.TWIPR_AddressTables.REGISTER_TABLE_GENERAL,
                                          address=addresses.TWIPR_ControlAddresses.ADDRESS_CONTROL_SET_SPEED_INPUT,
                                          data=data,
                                          input_type=twipr_control_speed_input)

    # ------------------------------------------------------------------------------------------------------------------
    def _setDirectInput_LL(self, u_left: float, u_right: float) -> None:
        assert (isinstance(u_left, float))
        assert (isinstance(u_right, float))
        data = {
            'u_left': u_left,
            'u_right': u_right
        }
        self._comm.serial.executeFunction(module=addresses.TWIPR_AddressTables.REGISTER_TABLE_GENERAL,
                                          address=addresses.TWIPR_ControlAddresses.ADDRESS_CONTROL_SET_DIRECT_INPUT,
                                          data=data,
                                          input_type=twipr_control_direct_input)

    # ------------------------------------------------------------------------------------------------------------------
    def _readControlConfig_LL(self) -> dict:
        return self._comm.serial.executeFunction(module=addresses.TWIPR_AddressTables.REGISTER_TABLE_GENERAL,
                                                 address=addresses.TWIPR_ControlAddresses.ADDRESS_CONTROL_READ_CONFIG,
                                                 data=None,
                                                 output_type=twipr_control_configuration_ll)

    # ------------------------------------------------------------------------------------------------------------------
    def _resetExternalInput(self):
        self.external_input.velocity.forward = 0
        self.external_input.velocity.turn = 0
        self.external_input.balancing.u_left = 0
        self.external_input.balancing.u_right = 0
        self.external_input.direct.u_left = 0
        self.external_input.direct.u_right = 0

    # ------------------------------------------------------------------------------------------------------------------
    def _updateLLSample(self, sample: BILBO_LL_Sample):
        # Check the STM32 Control State
        status_ll = TWIPR_Control_Status_LL(sample.control.status)

        if status_ll is not self.status_ll:
            ...

        self.status_ll = status_ll

        status = None
        if status_ll == TWIPR_Control_Status_LL.TWIPR_CONTROL_STATE_LL_ERROR:
            status = TWIPR_Control_Status.TWIPR_CONTROL_STATE_ERROR
        elif status_ll == TWIPR_Control_Status_LL.TWIPR_CONTROL_STATE_LL_NORMAL:
            status = TWIPR_Control_Status.TWIPR_CONTROL_STATE_NORMAL

        if status != self.status:
            self.callbacks.status_change.call(status, forced_change=True)

        # Check the STM32 Control Mode
        mode_ll = TWIPR_Control_Mode_LL(sample.control.mode)

        if mode_ll is not self.mode_ll:
            ...  # TODO

        self.mode_ll = mode_ll

        mode = None

        if mode_ll == TWIPR_Control_Mode_LL.TWIPR_CONTROL_MODE_LL_OFF:
            mode = TWIPR_Control_Mode.TWIPR_CONTROL_MODE_OFF
        elif mode_ll == TWIPR_Control_Mode_LL.TWIPR_CONTROL_MODE_LL_DIRECT:
            mode = TWIPR_Control_Mode.TWIPR_CONTROL_MODE_DIRECT
        elif mode_ll == TWIPR_Control_Mode_LL.TWIPR_CONTROL_MODE_LL_BALANCING:
            mode = TWIPR_Control_Mode.TWIPR_CONTROL_MODE_BALANCING
        elif mode_ll == TWIPR_Control_Mode_LL.TWIPR_CONTROL_MODE_LL_VELOCITY:
            mode = TWIPR_Control_Mode.TWIPR_CONTROL_MODE_VELOCITY

        # TODO: Here i should take into account if the Python Side has different modes than the LL side.
        # Then this not longer working
        if mode != self.mode:
            self._resetExternalInput()
            self.callbacks.mode_change.call(mode, forced_change=True)

        self.mode = mode

    # ------------------------------------------------------------------------------------------------------------------
    def _updateExternalInput(self, external_input: BILBO_Control_Input):

        input = BILBO_Control_Input()

        # Check if external Input settings is enabled
        if not self.enable_external_input:
            return input

        # Check the control mode
        if self.mode == TWIPR_Control_Mode.TWIPR_CONTROL_MODE_OFF:
            return
        elif self.mode == TWIPR_Control_Mode.TWIPR_CONTROL_MODE_DIRECT:
            input.direct = external_input.direct
        elif self.mode == TWIPR_Control_Mode.TWIPR_CONTROL_MODE_BALANCING:
            input.balancing = external_input.balancing
        elif self.mode == TWIPR_Control_Mode.TWIPR_CONTROL_MODE_VELOCITY:
            input.velocity = external_input.velocity

        return input

    # ------------------------------------------------------------------------------------------------------------------
    def _setInput(self, input: BILBO_Control_Input):

        # Check the control mode
        if self.mode == TWIPR_Control_Mode.TWIPR_CONTROL_MODE_OFF:
            return
        elif self.mode == TWIPR_Control_Mode.TWIPR_CONTROL_MODE_DIRECT:
            self._setDirectInput_LL(input.direct.u_left, input.direct.u_right)
        elif self.mode == TWIPR_Control_Mode.TWIPR_CONTROL_MODE_BALANCING:
            self._setBalancingInput_LL(input.balancing.u_left, input.balancing.u_right)
        elif self.mode == TWIPR_Control_Mode.TWIPR_CONTROL_MODE_VELOCITY:
            self._setSpeedInput_LL(input.velocity.forward, input.velocity.turn)

