# Temporary probe (Lindsey OK'd test runs 2026-11-08): check the Little Lids lists parse; prints counts only.
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
import update_reading as u
u.LITTLE_OUT = tempfile.mktemp()
u.write_little(u.fetch(u.LITTLE_QUERY, {}))
