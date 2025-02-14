from utils.network import getInterfaceIP

def main():
    ip = getInterfaceIP('wlan0')
    print(ip)

if __name__ == '__main__':
    main()