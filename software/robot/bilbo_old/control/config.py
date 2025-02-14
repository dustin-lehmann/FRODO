import dataclasses
import json
import os

from paths import control_config_path
from utils.dataclass_utils import analyze_dataclass, from_dict

TWIPR_CONTROL_VELOCITY_FORWARD_MAX = 3
TWIPR_CONTROL_VELOCITY_TURN_MAX = 5

@dataclasses.dataclass
class PID_Control_Config:
    Kp: float = 0
    Kd: float = 0
    Ki: float = 0

@dataclasses.dataclass
class Feedforward_Config:
    gain: float = 0
    dynamics: str = ''

@dataclasses.dataclass
class StateFeedback_Config:
    gain: list = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class SpeedControl_Config:
    feedback: PID_Control_Config = dataclasses.field(default_factory=PID_Control_Config)
    feedforward: Feedforward_Config = dataclasses.field(default_factory=Feedforward_Config)

@dataclasses.dataclass
class VelocityControl_Config:
    forward: SpeedControl_Config = dataclasses.field(default_factory=SpeedControl_Config)
    turn: SpeedControl_Config = dataclasses.field(default_factory=SpeedControl_Config)

@dataclasses.dataclass
class GeneralControl_Config:
    theta_offset: float = 0
    torque_offset: list = dataclasses.field(default_factory=lambda: [0, 0])

@dataclasses.dataclass
class SafetyControl_Config:
    max_speed: float = 100
    max_torque: float =  0.4



@dataclasses.dataclass
class ManualControlTorque_Config:
    forward_torque_gain: float =  0.3
    turn_torque_gain: float = 0.3

@dataclasses.dataclass
class ManualControlVelocity_Config:
    forward_velocity_gain: float = 1
    turn_velocity_gain: float = 5
    max_forward_velocity: float = 1.5
    max_turn_velocity: float = 5

@dataclasses.dataclass
class ManualControl_Config:
    torque: ManualControlTorque_Config = dataclasses.field(default_factory=ManualControlTorque_Config)
    velocity: ManualControlVelocity_Config = dataclasses.field(default_factory=ManualControlVelocity_Config)

@dataclasses.dataclass
class ControlConfig:
    name: str
    description: str = ''
    general: GeneralControl_Config = dataclasses.field(default_factory=GeneralControl_Config)
    safety: SafetyControl_Config = dataclasses.field(default_factory=SafetyControl_Config)
    manual: ManualControl_Config = dataclasses.field(default_factory=ManualControl_Config)
    statefeedback: StateFeedback_Config = dataclasses.field(default_factory=StateFeedback_Config)
    velocity_control: VelocityControl_Config = dataclasses.field(default_factory=VelocityControl_Config)

def generate_default_config():
    config = ControlConfig(name='default')
    config.description = 'This is the default control configuration with which the robot_old is stable and is properly working'
    config.general.theta_offset = 0
    config.general.torque_offset = [0, 0]
    config.statefeedback.gain = [0.12, 0.24, 0.04, 0.036,
                                 0.12, 0.24, 0.04, -0.036]
    config.velocity_control.forward.feedback.Kp = -0.06
    config.velocity_control.forward.feedback.Ki = -0.09
    config.velocity_control.forward.feedback.Kd = 0
    config.velocity_control.turn.feedback.Kp = -0.01
    config.velocity_control.turn.feedback.Ki = -0.12
    config.velocity_control.turn.feedback.Kd = 0
    save_config(config)


def write_config(config: ControlConfig):
    """
    Writes the control config data to the STM32
    """
    raise NotImplementedError("not implemented")

def read_config(name: str) -> ControlConfig:
    """
    Reads the control config data from the STM32
    """
    raise NotImplementedError("not implemented")

def load_config(name: str) -> ControlConfig:
    """
    Load a JSON configuration file and return a ControlConfig instance.

    Args:
        name (str): The path to the JSON configuration file.

    Returns:
        ControlConfig: An instance of the ControlConfig class populated with the data from the JSON file.
    """
    file = f"{control_config_path}/{name}.json"

    try:
        with open(file, 'r') as f:
            data = json.load(f)
        return from_dict(ControlConfig, data)
    except FileNotFoundError:
        print(f"Configuration file '{name}.json' not found.")
        raise
    except json.JSONDecodeError:
        print(f"Error decoding JSON from the file '{name}'.")
        raise
    except TypeError as e:
        print(f"Error creating ControlConfig from the data: {e}")
        raise

def save_config(config: ControlConfig):
    """
    Save the given ControlConfig dataclass instance to a JSON file.

    Args:
        config (ControlConfig): The configuration dataclass to save.
        path (str): The path where the JSON file will be saved.
    """

    file = f"{control_config_path}/{config.name}.json"

    try:
        with open(file, 'w') as file:
            json.dump(dataclasses.asdict(config), file, indent=4)
        print(f"Configuration successfully saved to {file}")
    except Exception as e:
        print(f"An error occurred while saving the configuration: {e}")


def get_all_configs() -> dict[str, ControlConfig]:
    try:
        # Ensure the folder exists
        if not os.path.isdir(control_config_path):
            raise FileNotFoundError(f"The folder '{control_config_path}' does not exist.")

        # List all files in the folder and filter .json files
        config_files = [
            os.path.splitext(file)[0]
            for file in os.listdir(control_config_path)
            if file.endswith(".json")
        ]
        output = {}
        for config_file in config_files:
            output[config_file] = load_config(config_file)
        return output
    except Exception as e:
        print(f"An error occurred: {e}")
        raise

if __name__ == '__main__':
    # generate_default_config()
    analyze_dataclass(ControlConfig, generate_figure=True)