#!/usr/bin/env python3
"""Versioned SLURM entry point for the corrected R4 template pipeline."""

import os
import runpy


if not os.environ.get("R4_RUN_DIR"):
    raise RuntimeError("R4_RUN_DIR must point to an isolated result directory")

runpy.run_path(
    os.path.join(os.path.dirname(__file__), "template_single_zip.py"),
    run_name="__main__",
)
