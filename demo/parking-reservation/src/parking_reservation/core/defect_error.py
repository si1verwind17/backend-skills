class DefectError(Exception):
    """A broken invariant (inconsistent result, vanished row): a bug, never a business outcome.

    Not mapped to a business code; the request boundary logs it once and answers INTERNAL_ERROR.
    """
