# Open items: locker-rental service

| Id | Question | Raised in | Blocks | Decide by | Owner | Recommendation | Assumption in force |
|---|---|---|---|---|---|---|---|
| OI-1 | Grace period before billing starts | phase 0 | no | phase 4 | Business | 5 minutes | 5 minutes |
| OI-2 | Failed-open auto-refund window | phase 0 | no | phase 4 | Business + Vendor | full refund if never opened | full refund if never opened |
| OI-3 | Retain ended rentals beyond 24 months? | phase 1 | no | phase 4 | Legal | keep 24 months then archive | keep 24 months then archive |
| OI-4 | Vendor callback auth scheme | phase 2 | no | phase 4 | Vendor + Tech | HMAC header per vendor docs | HMAC header per vendor docs |
| OI-5 | ORM vs raw SQL house style | phase 3 | phase 3 | phase 3 | Tech lead | raw SQL in .sql files | raw SQL in .sql files |
| OI-6 | Min-instances=1 idle cost sign-off | phase 3 | phase 3 | phase 3 | Business | accept | accepted |
