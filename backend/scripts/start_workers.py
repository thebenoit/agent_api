import os
import sys
import time
import signal
import multiprocessing
import subprocess
from typing import List
import psutil
from dotenv import load_dotenv

load_dotenv()


class WorkerManager:
    def __init__(self, num_workers: int, redis_url: str):
        self.num_workers = num_workers
        self.redis_url = redis_url
        self.processes = []
        self.shutdown_requested = False

    def start_worker(self, worker_id: int, redis_url: str) -> subprocess.Popen:
        """
        Démarre un processus worker RQ
        """

        env = os.environ.copy()
        env["WORKER_ID"] = str(worker_id)
        env["REDIS_URL"] = redis_url

        # Démarrer le worker dans un processus séparé
        process = subprocess.Popen(
            [sys.executable, "workers/scraping_workers.py"],
            env=env,
            preexec_fn=os.setsid,
        )

        print(f"Worker {worker_id} démarré avec PID {process.pid}")
        return process

    def stop_worker(self, process: subprocess.Popen, timeout: int = 10):
        """
        Arrete un worker avec timeout et force si nécessaire
        """
        try:
            # Envoyer un SIGTERM au groupe de processus
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)

            # Attendre avec timeout
            process.wait(timeout=timeout)
            print(f"Worker {process.pid} arrêté proprement")
        except subprocess.TimeoutExpired:
            print(f"Worker {process.pid} non arrêté proprement. Forçage...")
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            process.wait()
            print(f"Worker {process.pid} arrêté avec SIGKILL")
        except ProcessLookupError:
            print(f"Worker {process.pid} non trouvé. Il a peut-être déjà été arrêté.")

    def start_all_workers(self):
        """Démarre tous les workers"""
        print(f"Démarrage de {self.num_workers} workers RQ...")
        print(f"Redis URL: {self.redis_url}")

        for i in range(self.num_workers):
            if self.shutdown_requested:
                break
            process = self.start_worker(i, self.redis_url)
            self.processes.append(process)
            time.sleep(1)

        print(f"Tous les workers démarrés. Surveillance en cours...")

    def stop_all_workers(self):
        """Arrête tous les workers proprement"""
        print("Arrêt de tous les workers...")

        for process in self.processes:
            if process.poll() is None:  # Si le processus tourne encore
                self.stop_worker(process)

        self.processes.clear()
        print("Tous les workers arrêtés")

    def signal_handler(self, signum, frame):
        """Gestionnaire de signal robuste"""
        print(f"\nSignal {signum} reçu. Arrêt en cours...")
        self.shutdown_requested = True
        self.stop_all_workers()
        sys.exit(0)


    def run(self):
        """Point d'entrée principal avec gestion robuste des signaux"""
        # Configuration des signaux
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        try:
            self.start_all_workers()

            # Surveillance simple (sans redémarrage automatique)
            while not self.shutdown_requested:
                time.sleep(1)

        except KeyboardInterrupt:
            self.signal_handler(signal.SIGINT, None)
        except Exception as e:
            print(f"Erreur: {e}")
            self.stop_all_workers()
            sys.exit(1)


def main2():
    """Point d'entrée principal"""
    num_workers = int(os.getenv("NUM_WORKERS", 5))
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    manager = WorkerManager(num_workers, redis_url)
    manager.run()


if __name__ == "__main__":
    main2()
