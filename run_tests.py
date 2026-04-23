import subprocess
import sys

result = subprocess.run(
    [sys.executable, '-m', 'pytest', 
     'tests/utils/test_tokenizer.py',
     'tests/utils/test_llm_client.py', 
     'tests/utils/test_rate_limiter.py',
     '-v', '--tb=short'],
    capture_output=True,
    text=True,
    cwd='D:/KG_project/Final4.14'
)

with open('D:/KG_project/Final4.14/test_result.txt', 'w') as f:
    f.write("STDOUT:\n")
    f.write(result.stdout)
    f.write("\nSTDERR:\n")
    f.write(result.stderr)
    f.write(f"\nReturn code: {result.returncode}")