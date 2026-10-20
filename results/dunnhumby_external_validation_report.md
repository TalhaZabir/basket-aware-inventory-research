# dunnhumby external validation

This is a separate validation dataset and was not merged with UCI. The graph and popularity buffers are built from weeks 1–78 only; weeks 91–102 are replayed. Inventory, one-week lead time, costs, and alpha are synthetic assumptions.

| policy | alpha | test_weeks | total_cost | average_inventory_units | item_fill_rate | complete_basket_fill_rate | unmet_units | stockout_events | basket_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C4_popularity | 1.5 | 12 | 2909465549.0 | 240228774.08333334 | 1.0 | 1.0 | 0.0 | 0 | 22759 |
| PA_graph | 1.5 | 12 | 2909465585.0 | 240228777.08333334 | 1.0 | 1.0 | 0.0 | 0 | 22759 |

Retained 300 products, 181761 baskets, and 544550 transaction lines after restricting to the top-300 training-support universe.
