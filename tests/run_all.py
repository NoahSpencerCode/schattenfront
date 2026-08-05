"""Run the whole battery: python tests/run_all.py
Each case boots its own world in a subprocess; a nonzero exit from
any case fails the run."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

failed = []
cases = sorted(f for f in os.listdir(HERE)
               if f.startswith('case_') and f.endswith('.py'))
for case in cases:
    print("==== %s" % case)
    r = subprocess.run([PY, os.path.join(HERE, case)], cwd=HERE)
    if r.returncode != 0:
        failed.append(case)
print("=" * 40)
if failed:
    print("FAILED: %s" % ", ".join(failed))
    sys.exit(1)
print("ALL %d CASES GREEN" % len(cases))
