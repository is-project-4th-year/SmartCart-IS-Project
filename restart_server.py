#!/usr/bin/env python
import subprocess
import time
import os

# Kill existing process on port 5001
os.system('lsof -ti :5001 > /tmp/pids.txt 2>/dev/null')
try:
    with open('/tmp/pids.txt', 'r') as f:
        pids = f.read().strip().split('\n')
        for pid in pids:
            if pid:
                os.system(f'kill -9 {pid}')
                print(f"Killed PID {pid}")
except:
    pass

time.sleep(2)

# Start new server
os.chdir('/Users/cyrilmugada/Documents/market/smartcart')
subprocess.Popen(['python', 'run.py'], 
                stdout=open('/tmp/smartcart.log', 'w'),
                stderr=subprocess.STDOUT)
print("✓ Server restarted on http://127.0.0.1:5001")