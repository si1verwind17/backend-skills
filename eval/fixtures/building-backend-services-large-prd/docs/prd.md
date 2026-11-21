# PRD: Fieldhouse member platform

Version 1.4 · owner: Priya Natarajan (Head of Product) · approved for build

## 1. Overview

Fieldhouse runs co-working spaces: six locations today, twenty planned within
two years. Members book desks and meeting rooms, bring visitors, join
community events and raise help-desk tickets. Today this runs on a booking
SaaS, a spreadsheet of company seats, a paper visitor book and a shared
inbox. The SaaS contract ends in nine months; this platform replaces all
four.

Three clients use one backend: the member app (iOS, Android, web), the
front-desk tablet at each location, and the staff console (web).

## 2. Goals

- One account per person, across every location.
- Companies buy seats for their staff and see one invoice.
- Front desks stop using paper: every visitor and walk-in is logged.
- Location managers see occupancy and room use without exporting data.

## 3. Decisions already made

- **D1** — Billing runs on Stripe Billing (subscriptions, invoices, card and
  SEPA payments). Fieldhouse never stores card data.
- **D2** — Members sign in with an email magic link or with Google. No
  passwords.
- **D3** — Every location belongs to Fieldhouse; there are no franchises.
- **D4** — The member app is the only way members book; the front-desk
  tablet books only on a member's behalf.
- **D5** — Prices are in euros, VAT included, shown per location.

## 4. Users and roles

| Role | Scope | Can |
|---|---|---|
| Member | their account | book, invite visitors, RSVP, raise tickets |
| Company admin | their company | buy and assign seats, see the company invoice, book for colleagues |
| Front desk | one location | check visitors in, book on a member's behalf, log walk-ins |
| Community manager | one or more locations | publish events, take attendance |
| Location manager | one location | everything front desk and community manager can, plus reports, rooms and desks setup |
| Operator admin | all locations | plans, prices, roles, every report |

A person may hold several roles at different locations (a member who is also
front desk at one location).

## 5. Release plan

| Release | Features | Target |
|---|---|---|
| 1 | F1–F8 | before the SaaS contract ends |
| 2 | F9 Parking, F10 Catering, F11 Smart locks | six months after release 1 |

Release 2 features are described so the team knows where things are going;
they are not part of the first build.

## 6. Features

### F1 — Accounts, companies and roles (release 1)

- A person signs in with a magic link sent to their email, or with Google.
  A magic link works once and expires after 15 minutes.
- A profile holds name, email, phone (optional), photo (optional) and a
  preferred home location.
- A company has a name, a billing contact, a VAT number and a number of
  seats per plan. A company admin invites people by email; an invitation
  expires after 7 days and can be re-sent.
- A person belongs to at most one company at a time. Leaving a company
  frees their seat at the end of the current day.
- Individual members (no company) pay for themselves.
- Operator admins grant and revoke staff roles per location. A revoked
  role stops working immediately, including on devices already signed in.
- Deactivating an account cancels its future bookings and RSVPs, keeps its
  past records, and signs it out everywhere.
- Every staff action that changes another person's data (role changes,
  bookings on someone's behalf, refunds of credits, account deactivation)
  is recorded with who, what, when and the location, and kept for 2 years.

### F2 — Membership plans and billing (release 1)

- Plans: Hot desk (any free desk, any location in the member's region),
  Dedicated desk (one assigned desk at one location), Private office (a
  room for a company, priced per seat), Day pass (one day, one location).
- Each plan includes meeting-room credits per month (Hot desk 4, Dedicated
  desk 8, Private office 10 per seat, Day pass 0). Unused credits expire
  at the end of the month. Members can buy credit packs of 10.
- Subscriptions bill monthly in advance through Stripe. Changing plan
  mid-month is prorated by Stripe; the new plan's access starts at once.
- A company receives one invoice for all its seats; individual members
  receive their own.
- When a payment fails, the member (or company admin) is told at once and
  again after 3 and 6 days. After 7 days without payment, booking is
  suspended for every seat on that subscription until it is paid; the
  member can still sign in and see their invoices.
- Day passes are bought in the app and paid immediately; a day pass is not
  refundable once its day has started.
- Operator admins set prices per plan per location and can create a
  discount code (percentage, valid dates, maximum uses).

### F3 — Desk booking (release 1)

- Each location has floors; each floor has desks shown on a floor map.
  Desks are hot or dedicated.
- Hot-desk members book a desk for a morning (08:00–13:00), an afternoon
  (13:00–18:00) or a full day, up to 14 days ahead.
- A desk is never booked twice for overlapping times.
- A location has a hot-desk capacity per day set by its manager (fire
  regulations); bookings stop when it is reached.
- A booking can be cancelled until 09:00 on its day without a mark;
  cancelling later, or not showing up, counts as a no-show.
- A booking with no check-in by 11:00 (morning or full day) or 15:00
  (afternoon) is released for others and counts as a no-show.
- Three no-shows in 30 days block the member from booking more than 2 days
  ahead for the next 14 days.
- A company admin can book a block of adjacent desks for a team day; each
  team member then confirms or drops their own desk.
- Dedicated desks are assigned by the location manager; their holder needs
  no booking, but can release the desk for a day to the hot-desk pool.

### F4 — Meeting rooms (release 1)

- Rooms have a capacity, equipment (screen, video bar, whiteboard) and a
  credit cost per 30 minutes (1 credit for small rooms, 2 for large).
- Members book 30-minute slots between 07:00 and 21:00, up to 30 days
  ahead, paying with credits; with no credits left they pay by card at the
  room's euro price.
- A room is never booked twice for overlapping times.
- Recurring bookings repeat weekly for up to 12 weeks; each occurrence is
  charged when it takes place, not upfront.
- A booking must be checked in (app or room tablet) within 15 minutes of its
  start, or it is released and its credits are not returned.
- Cancelling at least 2 hours ahead returns the credits; later
  cancellations do not.
- The booker can add external guests by name and email; guests receive an
  invitation and are pre-registered as visitors (F5).
- Location managers can block rooms for maintenance; existing bookings in
  the block are cancelled with credits returned and the bookers told.

### F5 — Visitor check-in (release 1)

- Members pre-register visitors with name, email, date and the host.
- At arrival the visitor checks in on the front-desk tablet with the code
  from their invitation or by name; the host is notified at once.
- A company may require visitors to sign its NDA at check-in; the signed
  version and time are kept.
- Front desk can check in a walk-in visitor by entering their details and
  choosing a host.
- A visitor who has not checked out by 22:00 is checked out automatically.
- The visitor log is kept for 12 months, then deleted.
- Fire safety: front desk can show, at any moment, everyone checked in at
  the location (members with a desk booking checked in, and visitors).

### F6 — Community events (release 1)

- Community managers publish events with title, description, time,
  location, capacity and visibility (members only, or public with a
  sign-up link).
- Members RSVP; when an event is full, they join a waitlist. A cancelled
  RSVP promotes the first person on the waitlist, who is told.
- Public events take sign-ups from people without an account (name and
  email); these people are not members.
- Attendees are reminded 24 hours and 1 hour before.
- Community managers take attendance on the day; attendance feeds the
  reports.
- Cancelling an event tells everyone who RSVP'd or is waitlisted.

### F7 — Help desk (release 1)

- Members raise tickets in a category (wifi, printing, cleaning,
  facilities, billing, other) with a description and an optional photo.
- Each category routes to a location's staff (billing routes to operator
  admins).
- Each category has a response target set by the operator (for example
  wifi: first response within 1 business hour).
- Staff update a ticket's status (open, in progress, waiting for member,
  resolved); the member is told at each change.
- A resolved ticket reopens if the member replies within 7 days; after
  that, a reply opens a new ticket.
- Members rate a resolved ticket from 1 to 5.

### F8 — Notifications (release 1)

- Every notice in F1–F7 reaches the person by push (if they use the app),
  by email, and in an in-app inbox.
- Members choose, per topic (bookings, billing, visitors, events, help
  desk), which of push and email they want; the inbox always gets
  everything. Billing notices by email cannot be switched off.
- Quiet hours (default 21:00–07:00, member-adjustable) hold push notices
  until the morning, except visitor arrivals.
- The inbox keeps notices for 90 days.

### F9 — Parking (release 2)

- Some locations have parking spots; members book a spot for a day
  alongside a desk, paid per day.
- Spots with chargers cost more and are limited to 4 hours.

### F10 — Catering (release 2)

- Members order lunch from partner kitchens through the app by 10:30 for
  delivery at 12:30; the kitchen is paid through Fieldhouse.
- Room bookings can add catering for their attendees.

### F11 — Smart locks (release 2)

- Members open the building and their private office with their phone;
  access follows their plan, bookings and payment status.
- Visitors receive a one-day door pass.

## 7. Reports

- Daily occupancy per location (desks booked, checked in, no-shows).
- Room utilisation per room per week.
- Revenue per plan per location per month (from Stripe).
- Help-desk response-target compliance per category per location.
- Event attendance per community manager per month.

Location managers see their location; operator admins see all.

## 8. Non-functionals

- About 4,000 members today; 15,000 when twenty locations are open.
- Booking rush: most desk bookings for the next day happen between 17:00
  and 19:00, and check-ins between 08:30 and 09:30.
- The member app's booking and check-in must feel instant: under 300 ms for
  95% of requests.
- Available 99.5% during opening hours (07:00–22:00 local time).
- Members are in the EU: GDPR applies; a member can export or delete their
  data.

## 9. Environment

- No backend exists yet; the booking SaaS exports CSV only.
- The backend team is four engineers who have shipped services in both
  Kotlin and TypeScript; no language is decided.
- The company uses Google Workspace; no cloud provider is chosen yet.

## 10. Open questions from product

- Can a day pass be bought without creating an account?
- Do company admins see their employees' booking history, or only seat
  usage?
