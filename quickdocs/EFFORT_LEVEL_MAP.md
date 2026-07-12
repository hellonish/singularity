## Chat Mode:

| Limit                     | Instant |   Medium |  High |      Ultra |
| ------------------------- | ------: | -------: | ----: | ---------: |
| Max agent/tool steps      |       1 |        4 |     8 |         12 |
| Max output tokens         |     500 |    1,500 | 3,000 |      6,000 |
| Recent raw context        |      4K |      12K |   24K | 48K tokens |
| Retrieved old messages    |     0–2 |        5 |     8 |         15 |
| Retrieved document chunks |     0–3 |        6 |    10 |         20 |
| Max files searched        |       1 |        5 |    10 |         20 |
| Max calls per tool type   |       1 |        2 |     5 |          8 |
| Request timeout           |     20s |      60s |  180s |       420s |
| Compaction trigger        |     55% |      70% |   80% |        88% |
| Reasoning effort          | Minimal | Standard |  High |    Maximum |


## Research Mode: 

| Limit                        |      Instant |          Medium |        High |               Ultra |
| ---------------------------- | -----------: | --------------: | ----------: | ------------------: |
| Max research queries         |            5 |              20 |          60 |                 150 |
| Max sources collected        |           10 |              40 |         100 |                 250 |
| Max sources deeply processed |            5 |              20 |          50 |                 120 |
| Max parallel tasks           |            3 |               8 |          15 |                  25 |
| Max agent/workflow steps     |            6 |              15 |          30 |                  60 |
| Max search iterations        |            1 |               2 |           4 |                   8 |
| Max report sections          |            5 |              12 |          25 |                  50 |
| Max output tokens            |        1,500 |           4,000 |       8,000 |              16,000 |
| Max total runtime            |        2 min |           8 min |      20 min |              45 min |
| Max Modal containers per run |            3 |               8 |          15 |                  25 |
| Max retries per task         |            1 |               2 |           2 |                   3 |
| Citation verification        |        Basic |        Standard |      Strong |          Exhaustive |
| Contradiction checking       |           No |         Limited |         Yes |          Multi-pass |
| Best for                     | Quick lookup | Normal research | Deep report | Large investigation |
