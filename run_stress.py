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
    'stress_image_ingest.py',
    'stress_encryption.py',
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
        env = os.environ.copy()
        env['PYTHONPATH'] = ROOT + (os.pathsep + env['PYTHONPATH'] if 'PYTHONPATH' in env and env['PYTHONPATH'] else '')
        proc = subprocess.run([sys.executable, path], cwd=ROOT, env=env)
        if proc.returncode != 0:
            ok = False

    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()