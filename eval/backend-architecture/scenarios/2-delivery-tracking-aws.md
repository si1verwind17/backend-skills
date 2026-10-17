# Scenario 2: food-delivery order tracking (AWS)

Purpose: verify the skill's cloud-neutrality — recommendations must come
from the customer's cloud (AWS this time), not from memorized defaults.

**Prompt**: identical framing, with requirements replaced by:

> Design the architecture for a food-delivery order-tracking system, in
> <workdir>. The company runs on AWS. The team is comfortable with Go and
> TypeScript. Keep it practical — mid-sized system. Requirements:
>
> - Customers place orders and watch live status: placed → accepted →
>   picked_up → delivered (cancel from placed/accepted). Restaurants and
>   the customer app must both react when status changes; a partner
>   analytics company "may integrate later."
> - Couriers send location pings every few seconds while delivering; the
>   customer app shows courier position near-live.
> - Restaurant menus are read on every order screen; menus change a few
>   times a day.
> - Dispatch logic sometimes has two dispatchers manually reassigning the
>   same delivery at once, causing conflicting assignments.
> - A settlement job aggregates delivered orders continuously; it runs on
>   the company's existing EKS cluster.
> - Public APIs for customer/restaurant apps; internal dispatch service
>   calls order service frequently at high volume.
> - Ops wants low idle cost for the customer-facing parts.
>
> (Same artifact and non-interactive instructions as [Scenario 1](1-ticketing-gcp.md).)

**Checks:** the same as [Scenario 1](1-ticketing-gcp.md).
