# Tutor Marketplace — business brief (from the founder, meeting notes)

We're building a tutoring marketplace and it needs to feel effortless.
Students find a tutor, book a lesson, pay, done. Tutors set their weekly
availability and shouldn't ever get double-booked — that's the one thing
that kills trust.

Decisions we've already made and won't revisit: lessons are online-only
(video happens on Zoom, we just store the link — we are NOT building video),
payment is handled by Stripe (we never touch card data), and tutors are
vetted manually by our ops team before they can appear in search.

A lesson goes: booked, then it happens, then it's completed and the tutor
gets paid out. Students can cancel up to 24h before start for a full
refund; inside 24h there's no refund. We haven't decided the tutor's
no-show policy yet — someone from ops needs to own that. Also TBD: the
platform commission percentage.

When a lesson completes, our accounting system needs to know, and marketing
might want lesson data in the warehouse someday for cohort analysis.

The search experience must be fast and seamless. We expect maybe 200 tutors
and a few thousand students in year one; if it takes off, ten times that.
This is revenue-critical from day one. We're on AWS, small team, mostly
TypeScript. Oh, and reviews — students rate tutors after a completed
lesson, one review per lesson, editable for 48 hours. GDPR applies, we
have EU students.
