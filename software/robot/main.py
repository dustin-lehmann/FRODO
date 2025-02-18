import time

from robot.control.frodo_control import FRODO_Control_Mode
from robot.utilities.video_streamer.video_streamer import VideoStreamer
from robot.frodo import FRODO
from robot.definitions import FRODO_Model


def main():
    frodo = FRODO()
    frodo.init()
    frodo.start()


    frodo.control.setMode(FRODO_Control_Mode.NAVIGATION)
    streamer = VideoStreamer()
    streamer.image_fetcher = frodo.sensors.aruco_detector.getOverlayFrame
    streamer.start()
    #frodo.control.setSpeed(1,1)
    #time.sleep(2)
    #frodo.control.setSpeed(0,0)

    while True:
        time.sleep(1)


if __name__ == '__main__':
    main()
