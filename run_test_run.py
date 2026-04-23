import subprocess
import sys

result = subprocess.run(
    [sys.executable, '-m', 'pytest', 'tests/experts/test_safety_expert.py', '-v'],
    capture_output=True,
    text=True
)

with open('test_run_output.txt', 'w', encoding='utf-8') as f:
    f.write('STDOUT: ' + result.stdout + '\n')
    f.write('STDERR: ' + result.stderr + '\n')
    f.write('RETURN CODE: ' + str(result.returncode) + '\n')
