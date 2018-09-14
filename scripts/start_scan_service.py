#!/usr/bin/env python3

import sys
import os
import time

sys.path.append('./')
from utils import mailer

def main():

    pwd = os.getcwd()
    prog = "main.py"

    if not os.path.exists(prog):
        print("{} does not exist at current directory".format(prog))
        return False
    else:
        print("run {}/{}".format(os.getcwd(), prog))

    log_dir = "log"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    argv = []
    is_debug = False
    for arg in sys.argv[1:]:
        if arg == '-d' or arg == '-D':
            is_debug = True
        else:
            argv.append(arg)
    option = '-d' if is_debug else ''

    fail_count_map = {}

    while True:
        print("------------- {} ---------------".format(time.ctime()))
        for token_name in argv:
            print("check if {} scan service is started".format(token_name))
            if is_debug:
                cmd = "python3 -u {} {} {}".format(prog, option, token_name)
            else:
                cmd = "python3 -u {} {}".format(prog, token_name)
            found_result = os.popen("ps -ef | grep -v grep | grep '{}'".format(cmd)).read()

            if found_result == '':
                fail_count = fail_count_map[token_name] if token_name in fail_count_map else 0
                print("no, start {} scan service ({})".format(token_name, fail_count))

                os.system("nohup {} > /dev/null 2>&1 &".format(cmd))

                # sending mail when restart process
                if fail_count == 1 or fail_count == 2:
                    subject = "MVS {} Scan Service Restart Warning ({})".format(
                        token_name, fail_count)
                    body = "{} scan service stopped ({}) and try restart at {}".format(
                        token_name, fail_count, time.ctime())
                    print("{}\n{}".format(subject, body))
                    symbol = "Scan Service Process Monitor: {}".format(sys.argv[0])
                    mailer.send_mail(symbol, subject, body)

                fail_count_map[token_name] = fail_count + 1

                print("sleep 2 seconds after start {}\n".format(token_name))
                time.sleep(2)
            else:
                # re-count from 1, 0 stands for initial starting
                fail_count_map[token_name] = 1
                print("yes, {} scan service is already started".format(token_name))

        print("sleep 60 seconds for next loop\n-----------\n")
        time.sleep(60)

if __name__ == '__main__':
    main()
