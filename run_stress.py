import os
import sys
import subprocess


ROOT = os.path.dirname(os.path.abspath(__file__))
STRESS_DIR = os.path.join(ROOT, 'tests', 'stress')


SCRIPTS = [
    'stress_large_insert.py',
    'stress_concurrent_rw.py',
    'stress_mixed_operations.py',
    'stress_indexing.py',
]


def main():
    if not os.path.isdir(STRESS_DIR):
        print('Directory degli stress test non trovata:', STRESS_DIR)
        sys.exit(1)

    ok = True
    for script in SCRIPTS:
        path = os.path.join(STRESS_DIR, script)
        if not os.path.exists(path):
            print(f"Script stress mancante: {script}, salto.")
            continue
        print(f"\n=== Eseguo stress: {script} ===")
        # Imposta cwd alla root del progetto per importare il pacchetto locale
        proc = subprocess.run([sys.executable, path], cwd=ROOT)
        if proc.returncode != 0:
            ok = False

    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()