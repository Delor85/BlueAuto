import runpy

# Apply the deterministic functional patch, then restore the historical economical
# dashboard cadence. Fast field recovery is provided by event/staleness-driven wakeups,
# not by permanent 5-second dashboard polling.
runpy.run_path('.github/scripts/v291_field_recovery.py', run_name='__main__')
runpy.run_path('.github/scripts/v291_preserve_adaptive_poll.py', run_name='__main__')
