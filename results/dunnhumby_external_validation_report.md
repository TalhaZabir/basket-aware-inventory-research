# dunnhumby pipeline stress check

This is a separate pipeline stress check and was not merged with UCI. The graph and popularity buffers are built from weeks 1–78 only; weeks 91–102 are replayed. Inventory, one-week lead time, costs, and alpha are synthetic assumptions. It is not treated as replication or causal external validation because the complete-basket proxy is tied and the stock-tightening setup is not an observed inventory record.

| policy | alpha | test_weeks | total_cost | average_inventory_units | item_fill_rate | complete_basket_fill_rate | unmet_units | stockout_events | basket_count | top_n | stock_factor |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C4_popularity | 1.5 | 12 | 36787802.0 | 31697.083333333332 | 0.9625437430686457 | 1.0 | 1076353.0 | 1097 | 22759 | 300 | 0.01 |
| PA_graph | 1.5 | 12 | 278962394.0 | 31688.083333333332 | 0.026155589381181628 | 1.0 | 27984653.0 | 12 | 22759 | 300 | 0.01 |

Retained 300 products, 181761 baskets, and 544550 transaction lines after restricting to the top-300 training-support universe. Stock factor=0.01.
