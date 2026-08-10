import subprocess
import sys
import time
import urllib.request


process = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)

ok = False
try:
    time.sleep(6)
    with urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=5) as response:
        body = response.read().decode("utf-8")
        print(f"UVICORN_STARTUP_OK status={response.status} body={body}")
        ok = response.status == 200
finally:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    print("UVICORN_STOPPED")
    if process.stdout:
        output = process.stdout.read()
        if output:
            print("UVICORN_OUTPUT_BEGIN")
            print(output[-2000:])
            print("UVICORN_OUTPUT_END")

sys.exit(0 if ok else 1)