# Compile PyTeal and overwrite TEAL files
# Note that the paths to the TEAL files are in the PyTeal files
./.venv/bin/python ./pyteal/always_succeeds.py
./.venv/bin/python ./pyteal/capi_app.py
./.venv/bin/python ./pyteal/dao_app.py
./.venv/bin/python ./pyteal/capi_escrow.py
./.venv/bin/python ./pyteal/central_escrow.py
./.venv/bin/python ./pyteal/customer_escrow.py
./.venv/bin/python ./pyteal/investing_escrow.py
./.venv/bin/python ./pyteal/locking_escrow.py
