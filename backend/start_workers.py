
import os
import sys
import time
import signal
import multiprocessing
import subprocess
from typing import List
import psutil


def start_worker(worker_id: int, redis_url: str) -> None:
    """
    Démarre un processus worker RQ
    """
    
    env = os.environ.copy()
    env["Worker_ID"] = str(worker_id)
    env["REDIS_URL"] = redis_url
    
    #Démarrer le worker dans un processus séparé
    process = subprocess.Popen[(
        sys.executable,
        "workers/scraping_workers.py"
    ), env=env]
    
    print(f"Worker {worker_id} démarree avec PID {process.pid}")
    return process

def monitor_workers(processe: List[subprocess.Popen]):
    """
    Surveille les workers et redémarre si nécessaire
    """
    
    while True:
        for i, process in enumerate(processes):
            if process.poll() is not None:
                print(f"Worker {i} est mort (PID {process.pid}). Redémarrage...")
                
                #Redémarrer le worker
                redis_url = os.getenv("REDIS_URL")
                processes[i] = start_worker(i, redis_url)
        time.sleep(5)
                