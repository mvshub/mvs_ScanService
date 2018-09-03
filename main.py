from services.service import MainService
from utils.log.logger import Logger
import json
import signal
import traceback
import sys


def main(scan_token_name, is_debug):
    Logger.logFilename = "{}_log".format(scan_token_name)

    setting_filename = 'config/service.json'
    if is_debug:
        setting_filename = 'config/service_debug.json'
    Logger.get().info("Loading config: {}".format(setting_filename))

    settings = json.loads(open(setting_filename).read())
    for i in settings['scans']['services']:
        if i['coin'].lower() == scan_token_name.lower():
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
    is_debug = False
    if len(sys.argv) > 2:
        if sys.argv[2] == '-d' or sys.argv[2] == '-D':
            is_debug = True
    main(scan_token_name, is_debug)
