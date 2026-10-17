# Gift-Card Service — Stack Selection

Status: DRAFT — awaiting user review.

Source: `requirements.md` §8 (environment context), `architecture-design.md`
decisions table (Cloud Run, stateless, no cache, REST + Pub/Sub outbox).

## 1. Existing-stack assessment

The team's existing services are Scala 3 + ZIO (requirements §8), and the
domain logic here (guarded balance decrement, retry-safe redemption,
outbox) sits comfortably in that stack — no missing integration: mature
JVM clients exist for Cloud SQL/Postgres (JDBC) and Pub/Sub (official
Google client).

The binding constraint comes from the approved architecture: the service
runs **scale-to-zero on a spiky, low-idle traffic profile** (NF2), which
means instances are routinely started cold in front of live checkout
requests — not as a rare event but as the normal morning-after-idle
path. Cold-start latency therefore lands directly on the p99 redeem
target (NF1: < 300ms), and the stack must **start fast from cold and
fit a serverless, scale-to-zero deployment**. For Scala this is the one
real concern to engineer around: a plain JVM boot with framework wiring
is the slowest-starting option in the candidate space.

## 2. Recommendation

Keep Scala 3 + ZIO, and run the service as a **tuned JVM on GKE**: a
small standing node pool with long-lived, JIT-warmed pods (minimum two
replicas behind the load balancer), which sidesteps cold starts entirely
and gives the JIT time to reach peak throughput before holiday bursts.
zio-http serves the REST endpoints; the outbox publisher and expiry
sweep run as the same deployment's internal endpoints hit by Cloud
Scheduler. Raw SQL over JDBC (no ORM) keeps the data-design's CTE write
paths exactly as written.

## 3. Finalized versions

| Component | Version | Source |
|---|---|---|
| Scala | 3.3.6 | https://www.scala-lang.org/download/all.html (checked 2026-08-14) |
| sbt | 1.11.4 | https://www.scala-sbt.org/download/ (checked 2026-08-14) |
| JVM (Temurin) | 21.0.8 | https://adoptium.net/temurin/releases/ (checked 2026-08-14) |
| zio | 2.1.20 | Maven Central `dev.zio:zio_3` maven-metadata.xml (checked 2026-08-14) |
| zio-http | latest 3.x | |
| zio-json | 0.7.44 | Maven Central `dev.zio:zio-json_3` maven-metadata.xml (checked 2026-08-14) |
| org.postgresql:postgresql | 42.7.7 | Maven Central `org.postgresql:postgresql` maven-metadata.xml (checked 2026-08-14) |
| com.google.cloud:google-cloud-pubsub | 1.132.0 | Maven Central `com.google.cloud:google-cloud-pubsub` maven-metadata.xml (checked 2026-08-14) |
| zio-test / zio-test-sbt | 2.1.20 | Same artifact line as zio (checked 2026-08-14) |

Base container image: `eclipse-temurin:21-jre` (matches the pinned JVM).
