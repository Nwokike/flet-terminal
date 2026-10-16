"""Shared pytest setup for the flet-terminal contract suite."""

import logging

# The suite exercises controls headless, so every imperative update logs the
# expected "control_update: no page available" warning. Attach a NullHandler
# to stop them from reaching logging's lastResort stderr handler while still
# making them visible via --log-cli-level=WARNING.
logging.getLogger("flet_terminal").addHandler(logging.NullHandler())
