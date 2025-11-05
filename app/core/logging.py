import logging, sys

def setup_logging():
    fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    logging.basicConfig(level=logging.INFO, format=fmt, stream=sys.stdout)
