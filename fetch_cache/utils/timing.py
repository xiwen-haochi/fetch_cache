from datetime import datetime
import time
import functools


def timing_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        method = kwargs.get("method", "")
        endpoint = kwargs.get("endpoint", "")

        start_time = time.time()
        start_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

        result = func(*args, **kwargs)

        execution_time = time.time() - start_time
        print(f"Request Timing Details:")
        print(f"  - Method: {method} {endpoint}")
        print(f"  - Start Time: {start_datetime}")
        print(f"  - Duration: {execution_time:.3f} seconds")
        print(f"  - Cache Hit: {'No' if execution_time > 0.1 else 'Yes'}")

        return result

    return wrapper
