# Scenario 3: cancel-order with signed requests (config pressure)

Added 2026-10-03 to validate `7c31be1` (fail configuration at boot) and
`bd145fe` (constant-vs-config triage), which S1/S2 carry no pressure for.

**Prompt**: [Scenario 1](1-cancel-order-python.md) verbatim (Python), with these two bullets appended
to the requirements list:

> - The endpoint is called by an internal back-office tool that signs
>   every request: header `X-Signature` is the hex HMAC-SHA256 of the raw
>   request body, keyed with a shared secret the service receives through
>   the `CANCEL_HMAC_SECRET` environment variable. Reject requests whose
>   signature is missing or wrong.
> - An order can only be cancelled within 30 days of being placed.

**Checks**: [Scenario 1](1-cancel-order-python.md) checks 1–7, plus:

8. **Configuration fails at boot**: the HMAC secret is read and validated
   (present, non-empty) where the verifier/app is constructed, so a
   missing or empty secret stops startup — not discovered per request, not
   absorbed into the signature-rejection path; a missing/malformed/wrong
   signature is a typed rejection (401/403), never an escaping exception;
   no half-guarded verify (input wrapped while the config-derived key can
   still throw).
9. **Constant stays a constant**: the 30-day window is a named constant
   beside its use; promoting it to runtime configuration FAILS unless the
   output cites a requirement (no-deploy tunability or per-env variance) —
   none exists in the prompt.
