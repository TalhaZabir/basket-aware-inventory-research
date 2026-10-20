# Phase 5 mechanism report

## Stylised two-item mechanism

Let a basket require items 1 and 2. Let (A_i) indicate that item (i) is available at the demand event, with marginal availability (s_i=P(A_i=1)). Complete-basket service is

\[
P(A_1=1,A_2=1)=s_1s_2+\rho\sqrt{s_1(1-s_1)s_2(1-s_2)},
\]

where ρ is the correlation of availability indicators. At fixed marginal service, positive availability correlation raises complete-basket service; negative correlation lowers it. A basket-aware allocation can therefore add value at equal total inventory only when it changes the allocation toward the joint-service bottleneck and the resulting increase in complete-basket probability is larger than the loss elsewhere.

For a shortage penalty (p), the first-order condition for a small reallocation Δ between the two items is:

\[
pN\,\Delta P_{12} > h\,\Delta I + K\,\Delta E,
\]

where (N) is the number of relevant basket opportunities, (h) is weekly holding cost, ΔI is the change in average inventory, and ΔE is the change in order events. Under strict matched inventory and fixed ordering activity, the right side is approximately zero; under unmatched policies, the buffer must recover its holding, purchase, and ordering premium through lower unmet demand.

The empirical Phase 2 pattern is consistent with the mechanism but does not identify it causally. PA1 and PA2 improve matched item and basket service, while C4 popularity-only improves service even more and PA3 is near zero for basket fill. This indicates that concentration and marginal volume can explain a substantial part of the observed improvement; the data do not show that edge topology itself is the active mechanism.

**Acceptance status:** pass as a bounded analytical mechanism, not as a proof of optimality. The empirical regime is compatible with a service benefit from reallocating buffer mass, but the topology-specific condition is not established.
