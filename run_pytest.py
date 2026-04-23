import sys
import io

old_stdout = sys.stdout
sys.stdout = mystdout = io.StringIO()

import subprocess
result = subprocess.run(
    [sys.executable, '-m', 'pytest', 'tests/importer/test_entity_extractor.py', '-v'],
    capture_output=True,
    text=True,
    cwd='D:/KG_project/Final4.14'
)

sys.stdout = old_stdout

print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("RETURN CODE:", result.returncode)