import time

print(globals())
print('mainCtrl' in globals())

while mainCtrl.thread_continue:
    print(f"hello")
    time.sleep(1)
