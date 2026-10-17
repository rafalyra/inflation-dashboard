"""Generic validation checks plus each adapter's official answer-key checks.

A failed check stops the pipeline before export (CLAUDE.md, data integrity). Checks are
never loosened to make data pass; the mismatch is reported instead.
"""
