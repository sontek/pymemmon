# demo of process taking up too much memory
l = []
for i in range(1, 1000):
    l.append("*" * i * 1024)

import time
time.sleep(60)
