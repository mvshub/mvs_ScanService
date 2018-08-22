#!/usr/bin/env python3

import sys
import os
import time

def main():
    script_dir = os.path.split(os.path.realpath(__file__))[0]
    os.chdir(script_dir + "/..")

    pwd = os.getcwd()
    prog = "main.py"

    if not os.path.exists(prog):
        print("{}/{} does not exist".format(pwd, prog))
        return False
    else:
        print("run {}/{}".format(pwd, prog))

    log_dir = "log"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    while True:
        print("------------- {} ---------------".format(time.ctime()))
        for token_name in sys.argv[1:]:
            print("check if {} scan service is started".format(token_name))

            cmd = "python3 -u {} {}".format(prog, token_name)
            found_result = os.popen("ps -ef | grep -v grep | grep '{}'".format(cmd)).read()

            if found_result == '':
                print("no, start {} scan service".format(token_name))

                log_file = "{}/{}_scan.log".format(log_dir, token_name)
                os.system("nohup {} > {} 2>&1 &".format(cmd, log_file))

                print("sleep 2 seconds after start {}\n".format(token_name))
                time.sleep(2)
            else:
                print("yes, {} scan service is already started".format(token_name))

        print("sleep 60 seconds for next loop\n-----------\n")
        time.sleep(60)

if __name__ == '__main__':
    main()
