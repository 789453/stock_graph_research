# Edge Candidate Repair Report - chain_text

## 1. Summary
- **View Key**: `58563ca7113f`
- **Status**: ✅ SUCCESS
- **Nodes**: 5502
- **K**: 100
- **Total Edges**: 550200

## 2. Core Checks
| check | value | status |
|---|---:|---|
| self_node_edges | 0 | PASS |
| self_stock_edges | 0 | PASS |
| self_record_edges | 0 | PASS |
| mutual_ratio | 0.5765 | PASS |
| reverse_score_nonnull_ratio | 1.0000 | PASS |

## 3. Rank Bands
|              |      0 |
|:-------------|-------:|
| rank_051_100 | 275100 |
| rank_021_050 | 165060 |
| rank_011_020 |  55020 |
| rank_001_005 |  27510 |
| rank_006_010 |  27510 |

## 4. Near Duplicates
- **Count (score >= 0.999999)**: 930
- **Near Duplicate Pairs CSV**: `edge_layers/near_duplicate_edges.csv`

## 5. Invalidated Old Results
- Old `mutual_ratio=1.0` invalidated (current ratio is 0.5765)
- Old `reverse_score` dictionary bug fixed.

## 6. Safe to Continue
**YES**
