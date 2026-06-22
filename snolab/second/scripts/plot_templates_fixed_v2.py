#!/usr/bin/env python3
"""Versioned plotting entry point for corrected R4 template outputs."""

import os
import runpy


if not os.environ.get("R4_RUN_DIR"):
    raise RuntimeError("R4_RUN_DIR must point to an isolated result directory")

runpy.run_path(
    os.path.join(os.path.dirname(__file__), "plot_templates.py"),
    run_name="__main__",
)
