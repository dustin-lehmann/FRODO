import copy
import dataclasses
import math
import threading
import qmt
import numpy as np

from robot.communication.frodo_communication import FRODO_Communication
from robot.definitions import FRODO_Model
from robot.lowlevel.frodo_ll_messages import FRODO_LL_SAMPLE
from robot.sensing.aruco.aruco_detector import ArucoDetector, ArucoMeasurement
from robot.sensing.camera.pycamera import PyCameraType
from robot.utilities.orientation import is_mostly_z_axis
from utils.events import EventListener


@dataclasses.dataclass
class FRODO_ArucoMeasurement_processed:
    id: int
    translation_vec: np.ndarray
    psi: float


@dataclasses.dataclass
class FRODO_SensorsData:
    speed_left: float = 0
    speed_right: float = 0
    rpm_left: float = 0
    rpm_right: float = 0
    aruco_measurements: list[FRODO_ArucoMeasurement_processed] = dataclasses.field(default_factory=list)


# ======================================================================================================================
class FRODO_Sensors:
    aruco_detector: ArucoDetector
    communication: FRODO_Communication

    data: FRODO_SensorsData

    frodo_model: FRODO_Model
    _data_lock = threading.Lock()

    def __init__(self, communication: FRODO_Communication):
        self.communication = communication

        self.communication.callbacks.rx_stm32_sample.register(self._stm32_samples_callback)

        self.aruco_detector = ArucoDetector(camera_version=PyCameraType.V3,
                                            marker_size=0.08,
                                            image_resolution=(960, 540),
                                            Ts=0.1)

        self.aruco_detector_measurement_listener = EventListener(self.aruco_detector.events.new_measurement,
                                                                 self._arucoMeasurement_callback)

        self.data = FRODO_SensorsData()
        self.frodo_model = FRODO_Model()

    # ------------------------------------------------------------------------------------------------------------------
    def init(self):
        ...

    # ------------------------------------------------------------------------------------------------------------------
    def start(self):
        ...
        self.aruco_detector.start()
        self.aruco_detector_measurement_listener.start()

    # ------------------------------------------------------------------------------------------------------------------
    def getData(self):
        with self._data_lock:
            return copy.deepcopy(self.data)

    # ------------------------------------------------------------------------------------------------------------------
    def _process_aruco_measurements(self, measurements: list[ArucoMeasurement]):
        aruco_measurements = []

        for measurement in measurements:
            aruco_id = measurement.marker_id[0]
            # transform the position vector into 2D coordinates

            x_pos = measurement.translation_vec[0][2] + self.frodo_model.vec_origin_to_camera[0]
            y_pos = -measurement.translation_vec[0][0]

            pos_vector = np.asarray([x_pos, y_pos],
                                    dtype=np.float32)

            # Transform the rotation vector:
            angle = np.linalg.norm(measurement.rotation_vec)
            axis = measurement.rotation_vec / angle

            q_camera_marker = qmt.quatFromAngleAxis(angle, axis)

            q_ME_M = qmt.qmult(qmt.quatFromAngleAxis(angle=np.deg2rad(90), axis=np.asarray([0, 0, 1])),
                               qmt.quatFromAngleAxis(angle=np.deg2rad(90), axis=np.asarray([1, 0, 0])))

            q_CE_C = qmt.qmult(qmt.quatFromAngleAxis(angle=np.deg2rad(-90), axis=np.asarray([1, 0, 0])),
                               qmt.quatFromAngleAxis(angle=np.deg2rad(90), axis=np.asarray([0, 1, 0])))

            q_CE_ME = qmt.qmult(q1=qmt.qmult(q1=q_CE_C, q2=q_camera_marker),
                                q2=qmt.qinv(q_ME_M))

            axis = qmt.quatAxis(q_CE_ME).squeeze()
            angle = qmt.quatAngle(q_CE_ME)

            # Check if the axis is mostly around the z-axis
            if not is_mostly_z_axis(axis):
                continue

            psi = qmt.wrapToPi(-angle + np.deg2rad(180))[0]

            measurement_processed = FRODO_ArucoMeasurement_processed(id=aruco_id,
                                                                     translation_vec=pos_vector,
                                                                     psi=psi)
            aruco_measurements.append(measurement_processed)

        with self._data_lock:
            self.data.aruco_measurements = aruco_measurements

    # ------------------------------------------------------------------------------------------------------------------
    def _arucoMeasurement_callback(self, measurements, *args, **kwargs):
        # Process the aruco measurements to transform it to the robots geometry
        self._process_aruco_measurements(measurements)

    # ------------------------------------------------------------------------------------------------------------------
    def _stm32_samples_callback(self, data: FRODO_LL_SAMPLE):
        with self._data_lock:
            self.data.speed_left = data.drive.speed.left
            self.data.speed_right = data.drive.speed.right
            self.data.rpm_left = data.drive.rpm.left
            self.data.rpm_right = data.drive.rpm.right
