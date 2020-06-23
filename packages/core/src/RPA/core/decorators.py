import platform
from functools import wraps


def operating_system_required(*systems):
    """Decorator to restrict method for specified operating system

    :param systems: operating systems in string format
        e.g. "Linux,Darwin", default 'Windows'
    """
    systems = systems or ["Windows"]

    def _decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if platform.system() not in systems:
                raise NotImplementedError(
                    "Keyword '%s' works only with %s operating system(s)"
                    % (f.__name__, " or ".join(systems))
                )
            else:
                return f(*args, **kwargs)

        return wrapper

    return _decorator
