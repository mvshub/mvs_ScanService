from services.service import WalletService
from utils.log.logger import Logger
import json
import signal
import traceback


def main():
    settings = json.loads(open('config/service.json').read())
    service = WalletService(settings)

    def stop_signal(a, b):
        Logger.info('receive signal,%s,%s' % (a, b))
        service.stop()
    signal.signal(signal.SIGINT, stop_signal)

    try:
        service.start()
    except Exception as e:
        Logger.error('failed to start service,%s' % e)
        Logger.error('{}'.format(traceback.format_exc()))

    service.stop()
    Logger.info('end...')


if __name__ == '__main__':
    main()
