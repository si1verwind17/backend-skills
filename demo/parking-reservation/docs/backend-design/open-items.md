# Open items

| Id | Question | Raised in | Blocks | Decide by | Owner | Recommendation | Assumption in force |
|---|---|---|---|---|---|---|---|
| OI-22 | W1 locks a garage with `pg_advisory_xact_lock(1, garage_id::int)` but `garage.garage_id` is bigint and the feed supplies the ids, so a garage id of 2^31 or more could never be booked: may the feed be limited to ids up to 2147483647 (loader or CHECK), or should the lock use a bigint key? | phase 4 | phase 4 | phase 4 | Tech | limit the ids with a CHECK, the cheaper change | the API edge rejects garage ids above 2147483647 and the lock text stays in force |
| OI-1 | Is billing notified over Google Cloud Pub/Sub (a paid service) with the fields in UC6 AC1, who creates billing's subscription before the first completion, how long an outage must billing survive, and may topics be created? | phase 0 | no | phase 4 | Business, Billing team | Pub/Sub, at-least-once, billing deduplicates | Pub/Sub on GCP, UC6 AC1 fields, a subscription with the default 7-day retention created by billing before launch; nothing created by this run |
| OI-6 | How are drivers and staff authenticated, which front end (a paid service) verifies them and sets the caller's identity and role, and may any staff member read any garage? | phase 0 | no | phase 4 | Tech | the platform authenticates and passes caller identity and role | an authenticating front end sets trusted identity and role, and the service accepts `/v1/*` only from its account and `/internal/*` only from the scheduler's (AD6); R17; nothing created by this run |
| OI-8 | Sizing and latency targets? | phase 0 | no | phase 4 | Tech | NF2 and NF3 as proposed | NF2, NF3 as written |
| OI-11 | Does the app send a client-generated unique key with each reserve attempt? | phase 0 | no | phase 4 | Tech | yes, required | key required (R18) |
| OI-14 | Is the cloud GCP, and is Postgres hosted as Cloud SQL (a paid service)? | phase 0 | no | phase 4 | Tech | Cloud SQL | Cloud SQL; nothing created by this run |
| OI-15 | May the service scale to zero, or must an instance always run? | phase 0 | no | phase 4 | Tech | scale to zero | scale to zero accepted |
| OI-2 | Does the driver pick the spot, or the service? | phase 0 | no | phase 4 | Business | service assigns | service assigns any free spot in the garage (R9) |
| OI-3 | Window boundaries and past starts: touching windows allowed, start not before now? | phase 0 | no | phase 4 | Business | half-open windows, no past starts | R3, R5, R6, R19, R20 as written |
| OI-5 | Does a cancelled or completed reservation release its spot, including the rest of its window? | phase 0 | no | phase 4 | Business | yes, both release it | R4 as written |
| OI-7 | Who owns garage and spot data and which key does its feed upsert on, which time zone does each garage use, and which statuses does a day lookup show? | phase 0 | no | phase 4 | Business | external feed fills garages with a time zone, lookup shows all statuses | seeded out of band with the feed's ids supplied explicitly, all statuses shown (R16) |
| OI-18 | Is a spot's label numbered per garage (two garages may both have spot "A1") or globally? | phase 1 | no | phase 4 | Business | per garage | label unique within its garage only; ids are global |
| OI-4 | When may a driver check in, and may they check out after the window ends? | phase 0 | no | phase 4 | Business | check-in inside the window, check-out any time after | R10, R11 as written |
| OI-9 | Retention period for reservations and driver ids? | phase 0 | no | phase 4 | Legal | keep until a policy exists | kept indefinitely (NF5) |
| OI-10 | Is the out-of-scope list in requirements §9 complete and right? | phase 0 | no | phase 4 | Business | confirm | list as written |
| OI-12 | Does checking out complete a reservation, or does the window's end? | phase 0 | no | phase 4 | Business | checking out completes it | R15 as written |
| OI-13 | Which driver identifiers do staff and billing need, and may the service hold a plate or name? | phase 0 | no | phase 4 | Business, Legal | opaque driver id only, unless staff need a plate | opaque driver id only (NF4) |
| OI-16 | Do drivers need to read a single reservation, and may only its driver change or view it? | phase 0 | no | phase 4 | Business | yes, owner only | UC7, R13, R21 as written |
| OI-17 | Longest window and furthest advance booking? | phase 0 | no | phase 4 | Business | 24 hours and 30 days | R7, R8 as proposed |
| OI-19 | May a paid Cloud Scheduler job call the relay endpoint every minute? | phase 2 | no | phase 4 | Tech | yes | one-minute sweep; nothing created by this run |
| OI-20 | May a completion notice reach billing up to about two minutes after check-out in normal operation? | phase 2 | no | phase 4 | Billing team | yes | about two minutes accepted |
| OI-21 | Which Python version, web framework and organization or licensing standards do the team's existing services use? | phase 3 | no | phase 4 | Tech | the team's current ones if they differ from SD1 and SD2 | Python 3.14, FastAPI, no mandated standard (SD1, SD2) |
