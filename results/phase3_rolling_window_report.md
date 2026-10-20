# Three rolling-origin windows

    window  train_end test_start   test_end  products  test_weeks  graph_edges            policy  total_cost  average_inventory_units  item_fill_rate  complete_basket_fill_rate  unmet_units  stockout_frequency  validation_wape_selected
        W1 2010-12-27 2011-03-07 2011-05-30      2270          13       997623 PA1_deterministic  2716025.50            851271.538462        0.970904                   0.960755      24376.0            0.015903                  0.731205
        W1 2010-12-27 2011-03-07 2011-05-30      2270          13       997623  C4_deterministic  2715009.00            851226.153846        0.971228                   0.957076      24104.0            0.017249                  0.731205
        W2 2011-03-28 2011-06-06 2011-08-29      2560          13      1296463 PA1_deterministic  2798677.85            850704.538462        0.956340                   0.900195      38970.0            0.031034                  0.715606
        W2 2011-03-28 2011-06-06 2011-08-29      2560          13      1296463  C4_deterministic  2786310.60            850306.461538        0.959485                   0.907760      36163.0            0.030217                  0.715606
W3_primary 2011-06-27 2011-09-05 2011-12-05      2731          14      1437590 PA1_deterministic  3784125.35            858084.928571        0.940103                   0.919090      89015.0            0.038570                  0.667231
W3_primary 2011-06-27 2011-09-05 2011-12-05      2731          14      1437590  C4_deterministic  3763180.60            857418.857143        0.943350                   0.918355      84189.0            0.040272                  0.667231

W3 is the primary frozen window; W1 and W2 are robustness windows. All graph and popularity buffers are rebuilt from each window's training period.
