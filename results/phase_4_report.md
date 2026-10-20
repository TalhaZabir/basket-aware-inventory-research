# Phase 4 external validity report

The project now includes a separate dunnhumby Complete Journey pipeline. The documented public release mirror is recorded with its source URL, DbCL-1.0 statement, SHA-256 checksum, schema, and cleaning counts. The data are not merged with UCI because product IDs, households, retailer context, and units are unrelated.

The external pipeline retains the top 300 products by training active-week support and volume, uses weeks 1–78 for graph construction, weeks 79–90 for validation, and weeks 91–102 for replay. Its normalized one-week-lead-time simulation yields full item and basket fill for both the graph and popularity buffers, so it is a data-pipeline and transportability check rather than a discriminating replication of the UCI effect.

**Acceptance status:** pass for a second basket dataset and documented separate replay; not evidence of cross-retailer causal generalization.
