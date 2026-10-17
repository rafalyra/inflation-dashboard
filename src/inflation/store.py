"""Read and write canonical partitions and vintages (SPEC §4.1, storage).

Phase 1 writes partitions locally; Phase 2 points the same layout at the `data` branch.
Partitions are split by country and reference month so each release touches few files.
"""
