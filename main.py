from services.service import MainService
from utils.log.logger import Logger
import json
import signal
import traceback
import sys


def main(scan_token_name):
    settings = json.loads(open('config/service.json').read())
    for i in settings['scans']['services']:
        if i['coin'] == scan_token_name:
            i['enable'] = True
            break
    else:
        Logger.get().error("Unsupported token: {}".format(scan_token_name))
        assert(False)

    service = MainService(settings)

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
    scan_token_name = sys.argv[1]
    main(scan_token_name)
