from collections.abc import Iterable


def is_dict_like(obj):
    """Check if `obj` behaves like a dictionary."""
    return all(
        hasattr(obj, attr) for attr in ("__getitem__", "keys", "__contains__")
    ) and not isinstance(obj, type)


def is_list_like(obj):
    """Check if `obj` behaves like a list."""
    return isinstance(obj, Iterable) and not isinstance(obj, (str, bytes))


def is_namedtuple(obj):
    """Check if `obj` is a namedtuple."""
    return isinstance(obj, tuple) and hasattr(obj, "_fields")
