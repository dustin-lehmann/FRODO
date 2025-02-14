import time

from core.communication.wifi.tcp.tcp import TCP_Socket
from core.communication.wifi.wifi_connection import WIFI_Connection


def main():

    socket = TCP_Socket(server_address='192.168.8.200', server_port=6666)

    def rx_callback(data, *args, **kwargs):

        socket.send(data)

    socket.callbacks.rx.register(rx_callback)
    socket.start()
    socket.connect(address='192.168.8.200', port=6666)



    while True:
        time.sleep(1)


def test_wifi_connection():

    wifi_connection = WIFI_Connection()

    def rx_callback(data, *args, **kwargs):
        wifi_connection.send(data)

    wifi_connection.callbacks.rx.register(rx_callback)
    wifi_connection.start()

    while True:
        time.sleep(1)



if __name__ == '__main__':
    test_wifi_connection()