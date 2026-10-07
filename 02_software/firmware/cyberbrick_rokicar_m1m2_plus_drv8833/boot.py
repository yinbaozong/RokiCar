import gc

# Keep boot finite so raw REPL remains usable for firmware updates.
# MicroPython starts main.py after this file returns on normal boot.
gc.collect()
