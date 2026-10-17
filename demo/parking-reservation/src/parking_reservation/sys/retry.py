from collections.abc import Callable


def call_with_retry[T](operation: Callable[[], T], retry_on: tuple[type[Exception], ...], attempts: int) -> T:
    """Runs an idempotent operation up to `attempts` times, retrying only on the listed errors.

    The one in-process retry helper: no backoff, bounded by count, and only for operations the
    caller has shown to be safe to repeat. The last error propagates.
    """
    for _ in range(attempts - 1):
        try:
            return operation()
        except retry_on:
            continue
    return operation()
