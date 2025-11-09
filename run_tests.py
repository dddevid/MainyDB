import argparse
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))


def run_unit_tests(verbosity: int) -> bool:
    suite = unittest.defaultTestLoader.discover(
        os.path.join(ROOT, 'tests', 'unit'), pattern='test_*.py'
    )
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    return result.wasSuccessful()


def main():
    parser = argparse.ArgumentParser(description='Esegui gli unit test di MainyDB')
    parser.add_argument('-v', '--verbosity', type=int, default=2, help='Verbosità degli unit test (default: 2)')
    args = parser.parse_args()

    print('== Unit test ==')
    unit_ok = run_unit_tests(args.verbosity)
    sys.exit(0 if unit_ok else 1)


if __name__ == '__main__':
    main()