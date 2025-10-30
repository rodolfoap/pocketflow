import inspect, sys

def debug(message=""):
	fi = inspect.getframeinfo((inspect.stack()[1])[0]);
	print(f">>> [{fi.filename}] {fi.function}(): [{fi.lineno}] {message}", file=sys.stderr)
