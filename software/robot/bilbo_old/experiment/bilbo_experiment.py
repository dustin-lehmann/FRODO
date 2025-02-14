import dataclasses


@dataclasses.dataclass
class BILBO_TrajectoryData:
    ...
# === BILBO_ExperimentHandler =========================================================================================
class BILBO_ExperimentHandler:
    ...

    def __init__(self):
        ...



    def loadTrajectory(self) -> bool:
        ...

    def runTrajectory(self) -> bool:
        ...

    def getTrajectoryData(self) -> BILBO_TrajectoryData:
        ...