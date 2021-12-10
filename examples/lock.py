#!/usr/bin/env python
from __future__ import print_function

import sys
import threading
import weakref
import time
sys.path.append("../")
from pysyncobj import SyncObj, replicated, SyncObjConf
import asyncio
import sys
# import tornado
import tornado.ioloop
import tornado.web

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        # print("here!")
        self.write("Hello, world")

def make_app():
    print("making app")
    return tornado.web.Application([
        (r"/", MainHandler),
    ])

# if __name__ == "__main__":
#     app = make_app()
#     app.listen(8888)
#     tornado.ioloop.IOLoop.current().start()

class LockImpl(SyncObj):
    def __init__(self, selfAddress, partnerAddrs, autoUnlockTime, conf):
        super(LockImpl, self).__init__(selfAddress, partnerAddrs, conf=conf)
        self.__locks = {}
        self.__autoUnlockTime = autoUnlockTime
        self.__verbose = True

    @replicated
    def acquire(self, lockPath, clientID, currentTime):
        if self.__verbose:
            print(f"{threading.get_ident()} lock: {lockPath}, {clientID}, {currentTime}")
        existingLock = self.__locks.get(lockPath, None)
        # Auto-unlock old lock
        if existingLock is not None:
            if currentTime - existingLock[1] > self.__autoUnlockTime:
                existingLock = None
        # Acquire lock if possible
        if existingLock is None or existingLock[0] == clientID:
            self.__locks[lockPath] = (clientID, currentTime)
            return True
        # Lock already acquired by someone else
        return False

    @replicated
    def ping(self, clientID, currentTime):
        if self.__verbose:
            print(f"ping: {clientID}, {currentTime}, {self.__locks}")
        for lockPath in list(self.__locks.keys()):
            lockClientID, lockTime = self.__locks[lockPath]

            if currentTime - lockTime > self.__autoUnlockTime:
                del self.__locks[lockPath]
                continue

            if lockClientID == clientID:
                self.__locks[lockPath] = (clientID, currentTime)

    @replicated
    def release(self, lockPath, clientID):
        if self.__verbose:
            print(f"{threading.get_ident()} release: {lockPath} {clientID}")
        existingLock = self.__locks.get(lockPath, None)
        if existingLock is not None and existingLock[0] == clientID:
            del self.__locks[lockPath]

    @replicated
    def toggle_verbose(self):
        self.__verbose = not self.__verbose
        print(f"{threading.get_ident()} verbose: {self.__verbose}")

    def isOwned(self, lockPath, clientID, currentTime):
        existingLock = self.__locks.get(lockPath, None)
        if self.__verbose:
            print(existingLock, clientID)
        if existingLock is not None:
            if existingLock[0] == clientID:
                if currentTime - existingLock[1] < self.__autoUnlockTime:
                    return True
        return False

    def isAcquired(self, lockPath, clientID, currentTime):
        existingLock = self.__locks.get(lockPath, None)
        if self.__verbose:
            print(existingLock, clientID)
        if existingLock is not None:
            if currentTime - existingLock[1] < self.__autoUnlockTime:
                return True
        return False


class Lock(object):
    def __init__(self, selfAddress, partnerAddrs, autoUnlockTime, conf=None):
        self.__lockImpl = LockImpl(selfAddress, partnerAddrs, autoUnlockTime, conf=conf)
        self.__selfID = selfAddress
        self.__autoUnlockTime = autoUnlockTime
        self.__mainThread = threading.current_thread()
        self.__initialised = threading.Event()
        self.__thread = threading.Thread(target=Lock._autoAcquireThread, args=(weakref.proxy(self),))
        self.__thread.start()
        while not self.__initialised.is_set():
            pass

    def _autoAcquireThread(self):
        print(f"{threading.get_ident()} _autoAcquireThread")
        self.__initialised.set()
        try:
            while True:
                if not self.__mainThread.is_alive():
                    break
                time.sleep(float(self.__autoUnlockTime) / 4.0)
                if self.__lockImpl._getLeader() is not None:
                    self.__lockImpl.ping(self.__selfID, time.time())
        except ReferenceError:
            pass

    def tryAcquireLock(self, path):
        self.__lockImpl.acquire(path, self.__selfID, time.time())

    def isAcquired(self, path):
        return self.__lockImpl.isAcquired(path, self.__selfID, time.time())
    
    def isOwned(self, path):
        return self.__lockImpl.isOwned(path, self.__selfID, time.time())

    def release(self, path):
        self.__lockImpl.release(path, self.__selfID)

    def printStatus(self):
        self.__lockImpl._printStatus()

    def toggle_verbose(self):
        self.__lockImpl.toggle_verbose()

    def onTick(self, timeToWait):
        self.__lockImpl._onTick(timeToWait=0)

def printHelp():
    print('')
    print('        Available commands:')
    print('')
    print('help                 print this help')
    print('check lockPath       check if lock with lockPath path is ackquired or released')
    print('acquire lockPath     try to acquire lock with lockPath')
    print('release lockPath     try to release lock with lockPath')
    print('status               print lock status')
    print('verbose              toggle verbose debugging')
    print('')
    print('')


def main():
    if len(sys.argv) < 3:
        print('Usage: %s selfHost:port partner1Host:port partner2Host:port ...' % sys.argv[0])
        sys.exit(-1)

    selfAddr = sys.argv[1]
    partners = sys.argv[2:]

    conf = SyncObjConf(autoTick=False)

    lock = Lock(selfAddr, partners, 10.0, conf=conf)

    def get_input(v):
        if sys.version_info >= (3, 0):
            return input(v)
        else:
            return raw_input(v)

    def lock_status(path):
        if lock.isOwned(path):
            return "owned"
        elif lock.isAcquired(path):
            return "acquired"
        return "released"

    printHelp()
    while True:
        cmd = get_input(f"{threading.get_ident()} >> ").split()
        if not cmd:
            continue
        elif cmd[0] == 'help':
            printHelp()
        elif cmd[0] == 'check':
            print(lock_status(cmd[1]))
        elif cmd[0] == 'acquire':
            lock.tryAcquireLock(cmd[1])
            time.sleep(1.5)
            print(lock_status(cmd[1]))
        elif cmd[0] == 'release':
            lock.release(cmd[1])
            time.sleep(1.5)
            print(lock_status(cmd[1]))
        elif cmd[0] == 'status':
            lock.printStatus()
        elif cmd[0] == 'verbose':
            lock.toggle_verbose()




async def connect_stdin_stdout():
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    w_transport, w_protocol = await loop.connect_write_pipe(asyncio.streams.FlowControlMixin, sys.stdout)
    writer = asyncio.StreamWriter(w_transport, w_protocol, reader, loop)
    return reader, writer

# https://stackoverflow.com/questions/45419723/python-timer-with-asyncio-coroutine
class Timer:
    def __init__(self, timeout, callback):
        self._timeout = timeout
        self._callback = callback
        self._task = asyncio.ensure_future(self._job())

    async def _job(self):
        # await asyncio.sleep(self._timeout)
        await self._callback()
        self._task = asyncio.ensure_future(self._job())

    def cancel(self):
        self._task.cancel()


async def main():
    reader, writer = await connect_stdin_stdout()

    if len(sys.argv) < 3:
        print('Usage: %s selfHost:port partner1Host:port partner2Host:port ...' % sys.argv[0])
        sys.exit(-1)

    selfAddr = sys.argv[1]
    partners = sys.argv[2:]

    conf = SyncObjConf(autoTick=False)

    lock = Lock(selfAddr, partners, 10.0, conf=conf)

    def get_input(v):
        if sys.version_info >= (3, 0):
            return input(v)
        else:
            return raw_input(v)

    def lock_status(path):
        if lock.isOwned(path):
            return "owned"
        elif lock.isAcquired(path):
            return "acquired"
        return "released"

    async def timeout_callback():
        lock.onTick(conf.autoTickPeriod)
        # print("ontick")

    # timer = Timer(conf.autoTickPeriod*2, timeout_callback)
    timer = Timer(2, timeout_callback)

    printHelp()
    while True:
        res = await reader.read(100)
        res = res.decode('utf-8')
        res = res.strip()
        writer.write(res.encode('utf-8'))
        if not res:
            break

        cmd = res.split() #get_input(f"{threading.get_ident()} >> ").split()
        # writer.write(cmd.encode('utf-8'))
        if not cmd:
            continue
        elif cmd[0] == 'help':
            printHelp()
        elif cmd[0] == 'check':
            writer.write(lock_status(cmd[1]).encode('utf-8'))
        elif cmd[0] == 'acquire':
            lock.tryAcquireLock(cmd[1])
            time.sleep(1.5)
            writer.write(lock_status(cmd[1]).encode('utf-8'))
        elif cmd[0] == 'release':
            lock.release(cmd[1])
            time.sleep(1.5)
            writer.write(lock_status(cmd[1]).encode('utf-8'))
        elif cmd[0] == 'status':
            lock.printStatus()
        elif cmd[0] == 'verbose':
            lock.toggle_verbose()

        # writer.write(res)

# async def main():
#     while True:
#         await asyncio.sleep(1)


if __name__ == "__main__":

    import tornado.platform.asyncio

    tornado.platform.asyncio.AsyncIOMainLoop().install()

    app = make_app()
    selfAddr = int(sys.argv[1].split(":")[1]) + 1000
    print(f"port: {selfAddr}")
    app.listen(selfAddr)
    # tornado.ioloop.IOLoop.current().start()
    print('here again')
    # asyncio.get_event_loop().run_forever()
    # asyncio.run(main())

    loop = asyncio.get_event_loop()
    # asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()

# if __name__ == '__main__':
#     main()

