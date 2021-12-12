#!/usr/bin/env python
from __future__ import print_function

import asyncio
import threading
import time

import tornado.web

from lock import Lock
from pysyncobj import SyncObjConf


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")


class StatusHandler(tornado.web.RequestHandler):
    sync_lock = None

    def initialize(self, sync_lock):
        self.sync_lock = sync_lock

    def get(self):
        self.write(str(self.sync_lock.getStatus()))


class ToggleHandler(tornado.web.RequestHandler):
    sync_lock = None

    def initialize(self, sync_lock):
        self.sync_lock = sync_lock

    def get(self):
        if self.sync_lock.isOwned("/dog"):
            self.sync_lock.release("/dog")
        else:
            self.sync_lock.tryAcquireLock("/dog")
        self.write("toggled") #str(self.sync_lock.isOwned("/dog")))


def make_app(sync_lock):
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/status", StatusHandler, {'sync_lock': sync_lock}),
        (r"/toggle", ToggleHandler, {'sync_lock': sync_lock}),
    ])


async def wait_for_exit(main_control):
    while main_control.thread_continue:
        await asyncio.sleep(1)

def main(main_control):
    print(f"{threading.get_ident()} main")

    selfAddr = "localhost:10000"
    partners = ['localhost:10001', 'localhost:10002']

    conf = SyncObjConf(autoTick=True)

    sync_lock = Lock(selfAddr, partners, 10.0, conf=conf)

    app = make_app(sync_lock)
    web_port = int(selfAddr.split(":")[1]) + 1000
    print(f"port: {web_port}")
    while main_control.thread_continue:
        try:
            app.listen(web_port)
            break
        except Exception as e:
            print(e)
            time.sleep(1)

    print('here again')

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(wait_for_exit(main_control))
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
