#!/usr/bin/env python

import os, sys
import time
import daemon
import daemon.pidfile
import argparse
import signal
import logging

# https://raw.githubusercontent.com/ggmartins/dataengbb/master/python/daemon/daemon1


PATHCTRL = '/tmp/'  # path to control files pid and lock
parser = argparse.ArgumentParser(prog="monitor")

sp = parser.add_subparsers()
sp_start = sp.add_parser('start', help='Starts %(prog)s daemon')
sp_start.add_argument('name', type=str, help='name of daemon')
sp_start.add_argument('path', type=str, help='path to daemon main file')
sp_start.add_argument('-v', '--verbose', action='store_true', help='log extra information')

sp_stop = sp.add_parser('stop', help='Stops %(prog)s daemon')
sp_stop.add_argument('name', type=str, help='name of daemon')

sp_status = sp.add_parser('status', help='Show the status of %(prog)s daemon')
sp_status.add_argument('name', type=str, help='name of daemon')

sp_restart = sp.add_parser('restart', help='Restarts %(prog)s daemon')
sp_restart.add_argument('name', type=str, help='name of daemon')

sp_debug = sp.add_parser('debug', help='Starts %(prog)s daemon in debug mode')
sp_debug.add_argument('-v', '--verbose', action='store_true', help='log extra information')
sp_debug.add_argument('name', type=str, help='name of daemon')




class MainCtrl:
    thread_continue = True
    thread_token = "token"


def main_thread(args, mainctrl, log):
    verbose = False

    if hasattr(args, 'verbose'):
        verbose = args.verbose

    if verbose:
        log.info("ARGS:{0}".format(args))
    try:
        with open(main_path, "r") as fp:
            with open(fp.read(), "r") as f:
                q = f.read()
                print(q)
                d = compile(q, 'main.py', 'exec')
        print(d)
        while mainctrl.thread_continue:
            if verbose:
                log.info("TOKEN:{0}".format(mainctrl.thread_token))
            # time.sleep(1)
            eval(d, {'mainCtrl': mainctrl})
    except KeyboardInterrupt as ke:
        if verbose:
            log.warning("Interrupting...")
    except Exception as e:
        if verbose:
            log.error("Exception:{0}".format(str(e)))
    log.info("Exiting...")


def daemon_start(args):
    mainctrl = MainCtrl()

    def main_thread_stop(signum=None, frame=None):
        mainctrl.thread_continue = False
        mainctrl.thread_token = "test"
        print("TOKEN:{0}".format(mainctrl.thread_token))

    if not os.path.exists(main_path):
        with open(main_path, "w") as f:
            f.write(args.path)

    print("INFO: {0} Starting ...".format(args.name))
    if os.path.exists(pidpath):
        print("INFO: {0} already running (according to {1}).".format(args.name, pidpath))
        sys.exit(1)
    else:
        with open(log_stdout, 'w') as f_stdout:
            with open(log_stderr, 'w') as f_stderr:
                with daemon.DaemonContext(
                        stdout=f_stdout,
                        stderr=f_stderr,
                        signal_map={
                            signal.SIGTERM: main_thread_stop,
                            signal.SIGTSTP: main_thread_stop,
                            signal.SIGINT: main_thread_stop,
                            # signal.SIGKILL: daemon_stop, #SIGKILL is an Invalid argument
                            signal.SIGUSR1: daemon_status,
                            signal.SIGUSR2: daemon_status,
                        },
                        pidfile=daemon.pidfile.PIDLockFile(pidpath)
                ):
                    logging.basicConfig(format='%(asctime)s.%(msecs)03d %(levelname)s {%(module)s} [%(funcName)s] %(message)s',
                                        datefmt='%Y-%m-%dT%H:%M:%S',
                                        filename=logpath,
                                        # filemode='w',
                                        level=logging.INFO)

                    log = logging.getLogger(__name__)
                    main_thread(args, mainctrl, log)


def daemon_restart(args):
    print("INFO: {0} Restarting...".format(args.name))
    daemon_stop(args)
    time.sleep(1)
    daemon_start(args)


def daemon_stop(args):
    print("INFO: {0} Stopping with args {1}".format(args.name, args))
    if os.path.exists(pidpath):
        with open(pidpath) as pid:
            try:
                os.kill(int(pid.readline()), signal.SIGINT)
            except ProcessLookupError as ple:
                os.remove(pidpath)
                print("ERROR ProcessLookupError: {0}".format(ple))
    else:
        print("ERROR: process isn't running (according to the absence of {0}).".format(pidpath))


def daemon_debug(args):
    print("INFO: running in debug mode.")
    log = logging.getLogger(__name__)
    mainctrl = MainCtrl()
    main_thread(args, mainctrl, log)


def daemon_status(args):
    print("INFO: {0} Status {1}".format(args.name, args))
    if os.path.exists(pidpath):
        print("INFO: {0} is running".format(args.name))
    else:
        print("INFO: {0} is NOT running.".format(args.name))


sp_stop.set_defaults(callback=daemon_stop)
sp_status.set_defaults(callback=daemon_status)
sp_start.set_defaults(callback=daemon_start)
sp_restart.set_defaults(callback=daemon_restart)
sp_debug.set_defaults(callback=daemon_debug)

args = parser.parse_args()

logpath = os.path.join(PATHCTRL, args.name + ".log")
log_stdout = os.path.join(PATHCTRL, args.name + ".out")
log_stderr = os.path.join(PATHCTRL, args.name + ".err")
pidpath = os.path.join(PATHCTRL, args.name + ".pid")
main_path = os.path.join(PATHCTRL, args.name + ".main.path")

if hasattr(args, 'callback'):
    args.callback(args)
else:
    parser.print_help()
