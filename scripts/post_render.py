"""Run after Quarto renders the site. Locks tutorial answer keys if the lock script is present."""
import pathlib
import runpy

lock = pathlib.Path(__file__).with_name("lock_keys.py")
if lock.exists():
    runpy.run_path(str(lock), run_name="__main__")
