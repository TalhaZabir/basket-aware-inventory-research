# Graphical abstract specification

**Question:** Does basket structure add value beyond popularity in multi-item replenishment?

**Observed data:** UCI transaction baskets → training-only weekly demand and co-purchase graph.

**Controlled replay:** popularity-only control (C4) | matched independent control (C1) | graph-on-popularity policy (PA1) → 4 x 3 lead-time and cost settings.

**Main finding:** graph signal is present, but is subsumed by popularity at matched inventory.

**Conditional finding:** graph information helps in the exploratory low-popularity/high-lift regime; it does not help when high-volume basket hubs already receive protection.

**Boundary:** simulated inventory and lead times; no claim of causal complementarity or historical cost savings.
