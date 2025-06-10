import functools


def track_events(*allowed_events: str):
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if allowed_events:
                request._allowed_conversion_events = set(allowed_events)
            else:
                request._allowed_conversion_events = None

            try:
                return view_func(request, *args, **kwargs)
            finally:
                if hasattr(request, "_allowed_conversion_events"):
                    delattr(request, "_allowed_conversion_events")

        return wrapper

    if len(allowed_events) == 1 and callable(allowed_events[0]):
        view_func = allowed_events[0]
        allowed_events = ()
        return decorator(view_func)
    else:
        return decorator
