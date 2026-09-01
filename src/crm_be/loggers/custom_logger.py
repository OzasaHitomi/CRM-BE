import logging

_log_format = "[%(asctime)s] [%(filename)s:%(funcName)s:%(lineno)d] %(levelname)s:     %(message)s"
_formatter = logging.Formatter(_log_format)

_handler = logging.StreamHandler()
_handler.setFormatter(_formatter)

logger = logging.getLogger("crm_be")
logger.addHandler(_handler)
logger.setLevel(logging.INFO)
logger.propagate = False
