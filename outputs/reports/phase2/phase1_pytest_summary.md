# Phase 1 Pytest Summary

**Run Time**: 2026-05-10 14:31:28

**Status**: FAILED


## Output

```

============================= test session starts ==============================
platform linux -- Python 3.11.15, pytest-9.0.3, pluggy-1.6.0 -- /home/purple_born/miniforge3/envs/py311/bin/python3
cachedir: .pytest_cache
rootdir: /home/purple_born/QuantSum/stock_graph_research
plugins: anyio-4.13.0
collecting ... collected 5 items

tests/test_market_alignment_contract.py::test_market_alignment_contract FAILED [ 20%]
tests/test_plotting_reads_cache_only.py::test_plotting_reads_cache_only FAILED [ 40%]
tests/test_real_knn_cache_contract.py::test_real_knn_cache_contract FAILED [ 60%]
tests/test_real_node_alignment.py::test_real_node_alignment FAILED       [ 80%]
tests/test_real_semantic_contract.py::test_real_semantic_contract FAILED [100%]

=================================== FAILURES ===================================
________________________ test_market_alignment_contract ________________________
tests/test_market_alignment_contract.py:13: in test_market_alignment_contract
    config = load_config(config_path)
             ^^^^^^^^^^^^^^^^^^^^^^^^
src/semantic_graph_research/config.py:8: in load_config
    raise FileNotFoundError(f"Config file not found: {config_path}")
E   FileNotFoundError: Config file not found: /home/purple_born/QuantSum/stock_graph_research/configs/phase1_semantic_graph.yaml
________________________ test_plotting_reads_cache_only ________________________
tests/test_plotting_reads_cache_only.py:13: in test_plotting_reads_cache_only
    config = load_config(config_path)
             ^^^^^^^^^^^^^^^^^^^^^^^^
src/semantic_graph_research/config.py:8: in load_config
    raise FileNotFoundError(f"Config file not found: {config_path}")
E   FileNotFoundError: Config file not found: /home/purple_born/QuantSum/stock_graph_research/configs/phase1_semantic_graph.yaml
_________________________ test_real_knn_cache_contract _________________________
tests/test_real_knn_cache_contract.py:13: in test_real_knn_cache_contract
    config = load_config(config_path)
             ^^^^^^^^^^^^^^^^^^^^^^^^
src/semantic_graph_research/config.py:8: in load_config
    raise FileNotFoundError(f"Config file not found: {config_path}")
E   FileNotFoundError: Config file not found: /home/purple_born/QuantSum/stock_graph_research/configs/phase1_semantic_graph.yaml
___________________________ test_real_node_alignment ___________________________
tests/test_real_node_alignment.py:13: in test_real_node_alignment
    config = load_config(config_path)
             ^^^^^^^^^^^^^^^^^^^^^^^^
src/semantic_graph_research/config.py:8: in load_config
    raise FileNotFoundError(f"Config file not found: {config_path}")
E   FileNotFoundError: Config file not found: /home/purple_born/QuantSum/stock_graph_research/configs/phase1_semantic_graph.yaml
_________________________ test_real_semantic_contract __________________________
tests/test_real_semantic_contract.py:12: in test_real_semantic_contract
    config = load_config(config_path)
             ^^^^^^^^^^^^^^^^^^^^^^^^
src/semantic_graph_research/config.py:8: in load_config
    raise FileNotFoundError(f"Config file not found: {config_path}")
E   FileNotFoundError: Config file not found: /home/purple_born/QuantSum/stock_graph_research/configs/phase1_semantic_graph.yaml
=========================== short test summary info ============================
FAILED tests/test_market_alignment_contract.py::test_market_alignment_contract
FAILED tests/test_plotting_reads_cache_only.py::test_plotting_reads_cache_only
FAILED tests/test_real_knn_cache_contract.py::test_real_knn_cache_contract - ...
FAILED tests/test_real_node_alignment.py::test_real_node_alignment - FileNotF...
FAILED tests/test_real_semantic_contract.py::test_real_semantic_contract - Fi...
============================== 5 failed in 1.19s ===============================

```
