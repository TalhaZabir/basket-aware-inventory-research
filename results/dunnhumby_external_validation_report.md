# dunnhumby external validation

This is a separate validation dataset and was not merged with UCI. The graph and popularity buffers are built from weeks 1–78 only; weeks 91–102 are replayed. Inventory, one-week lead time, costs, and alpha are synthetic assumptions.

| policy | alpha | test_weeks | total_cost | average_inventory_units | item_fill_rate | complete_basket_fill_rate | unmet_units | stockout_events | basket_count | top_n | stock_factor |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C4_popularity | 1.5 | 12 | 46614146.0 | 13676.166666666666 | 0.9482350698588312 | 1.0 | 1722239.0 | 3544 | 26528 | 1000 | 0.01 |
| PA_graph | 1.5 | 12 | 320801624.0 | 13668.166666666666 | 0.032547176644981114 | 1.0 | 32187525.0 | 48 | 26528 | 1000 | 0.01 |

Retained 1000 products, 212095 baskets, and 886241 transaction lines after restricting to the top-1000 training-support universe. Stock factor=0.01.
