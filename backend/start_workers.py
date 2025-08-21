
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
        
def main():
    """Point d'entrée principal"""
    
    # Configuration
    num_workers = int(os.getenv("NUM_WORKERS", 5))  # 5 workers par défaut
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    print(f"Démarrage de {num_workers} workers RQ...")
    print(f"Redis URL: {redis_url}")
    
    # Démarrer tous les workers
    processes = []
    for i in range(num_workers):
        process = start_worker_process(i, redis_url)
        processes.append(process)
        time.sleep(1)  # Délai entre les démarrages
    
    print(f"Tous les workers démarrés. Surveillance en cours...")
    
    # Gestion des signaux pour arrêt propre

    # Gestion des signaux pour arrêt propre
def signal_handler(signum, frame):
        print(f"\nSignal {signum} reçu. Arrêt des workers...")
        for process in processes:
            if process.poll() is None:
                process.terminate()
                process.wait()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Surveiller les workers
    try:
        monitor_workers(processes)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main()               