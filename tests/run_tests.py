#!/usr/bin/env python3
"""
Perfect test runner for ROAMDP-compliant SomaBrain test suite.

Usage:
    python tests/run_tests.py           # Run all tests
    python tests/run_tests.py --core    # Run only core tests
    python tests/run_tests.py --e2e     # Run only E2E tests
    python tests/run_tests.py --perf    # Run performance tests
    python tests/run_tests.py --sleep   # Run sleep system tests
"""

import subprocess
import sys
import argparse
from pathlib import Path


def run_tests(args):
    """Execute test suite with perfect configuration."""
    
    test_dirs = {
        'all': ['tests/core', 'tests/e2e', 'tests/performance'],
        'core': ['tests/core'],
        'e2e': ['tests/e2e'],
        'perf': ['tests/performance'],
        'sleep': ['tests/core/test_sleep_system.py']
    }
    
    dirs = test_dirs.get(args.mode, test_dirs['all'])
    
    # Build pytest command
    cmd = [
        'pytest',
        '--tb=short',
        '--strict-markers',
        '-v'
    ]
    
    if args.coverage:
        cmd.extend(['--cov=somabrain', '--cov-report=term-missing'])
    
    if args.performance:
        cmd.extend(['-m', 'performance'])
    else:
        cmd.extend(['-m', 'not performance'])
    
    cmd.extend(dirs)
    
    print(f"Running tests: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    
    if result.returncode != 0:
        print("❌ Some tests failed")
        return result.returncode
    
    print("✅ All tests passed perfectly")
    return 0


def main():
    parser = argparse.ArgumentParser(description='Perfect SomaBrain test runner')
    parser.add_argument(
        '--mode',
        choices=['all', 'core', 'e2e', 'perf', 'sleep'],
        default='all',
        help='Test mode selection'
    )
    parser.add_argument(
        '--coverage',
        action='store_true',
        help='Generate coverage report'
    )
    parser.add_argument(
        '--performance',
        action='store_true',
        help='Include performance tests'
    )
    
    args = parser.parse_args()
    
    return run_tests(args)


if __name__ == '__main__':
    sys.exit(main())