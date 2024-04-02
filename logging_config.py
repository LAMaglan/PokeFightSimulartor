# logging_config.py
import logging
import sys

def get_logger(name: str):
    # Create a logger object.
    logger = logging.getLogger(name)

    # Set the log level.
    logger.setLevel(logging.INFO)

    # Create a stream handler that logs to stdout.
    stream_handler = logging.StreamHandler(sys.stdout)

    # Optionally set the log level for the stream handler.
    stream_handler.setLevel(logging.INFO)

    # Create a formatter.
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Set the formatter for the stream handler.
    stream_handler.setFormatter(formatter)

    # Add the stream handler to your logger.
    logger.addHandler(stream_handler)

    # Optional: output logging to specified file
    # file_handler = logging.FileHandler('pokefightsimulator.log')
    # file_handler.setFormatter(formatter)
    # file_handler.setLevel(logging.INFO)
    # logger.addHandler(file_handler)

    return logger