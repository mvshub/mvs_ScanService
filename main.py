from services.service import WalletService
from utils.log.logger import Logger
import json
import signal
import traceback


def main():
    settings = json.loads(open('config/service.json').read())
    service = WalletService(settings)

    def stop_signal(a, b):
        Logger.get().info('receive signal,%s,%s' % (a, b))
        service.stop()
    signal.signal(signal.SIGINT, stop_signal)

    try:
        service.start()
    except Exception as e:
        Logger.get().error('failed to start service,%s' % e)
        Logger.get().error('{}'.format(traceback.format_exc()))

    service.stop()
    Logger.get().info('end...')


if __name__ == '__main__':
    main()
