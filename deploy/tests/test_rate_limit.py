import concurrent.futures
import urllib.request
import urllib.error
from collections import Counter

URL = "http://127.0.0.1/api/health"
REQUESTS = 30

def send_request(_):
    try:
        with urllib.request.urlopen(URL, timeout=5) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code
    except Exception as error:
        return f"ERROR: {error}"

with concurrent.futures.ThreadPoolExecutor(
    max_workers=REQUESTS
) as executor:
    results = list(executor.map(send_request, range(REQUESTS)))

print(f"Total requests: {REQUESTS}")

for status, count in sorted(
    Counter(results).items(),
    key=lambda item: str(item[0])
):
    print(f"HTTP {status}: {count}")
