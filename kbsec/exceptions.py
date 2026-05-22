class KBSecConfigError(Exception):
    pass

class KBConnectionError(Exception):
    pass

class KBTimeoutError(Exception):
    pass

class KBSecRequestError(Exception):
    pass

# Aliases for backward compat
KBSecConnectionError = KBConnectionError
