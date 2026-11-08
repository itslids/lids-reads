# Temporary probe (Lindsey OK'd 2026-11-08): run the new Little Lids part against Hardcover and show the result.
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
import update_reading as u
u.LITTLE_OUT = tempfile.mktemp()
u.write_little(u.fetch(u.LITTLE_QUERY, {}))
print(open(u.LITTLE_OUT).read())
