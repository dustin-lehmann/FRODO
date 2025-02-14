import time

from robot.control.frodo_control import FRODO_Control_Mode
from robot.frodo import FRODO
from robot.definitions import FRODO_Model


def main():
    frodo = FRODO()
    frodo.init()
    frodo.start()


    frodo.control.setSpeed(1,1)
    time.sleep(2)
    frodo.control.setSpeed(0,0)

    while True:
        time.sleep(1)


if __name__ == '__main__':
    main()
