"""Apply the fictional v1.9.1 fix to your working copy (run from repo root).

Changes: orders-submit reserves inventory with a 1-second client timeout and
fails open; APP_VERSION becomes 1.9.1. The OrdersSubmitTimeout default stays
at 10 seconds (if a working copy still says 3, it is set back to 10).
"""
import pathlib
import re
import shutil

root = pathlib.Path(__file__).resolve().parent.parent
template = root / "template.yaml"
text = template.read_text()
text = re.sub(r'(OrdersSubmitTimeout:\s*\n\s*Type: Number\s*\n\s*Default: )\d+', r"\g<1>10", text)
text = re.sub(r'APP_VERSION: "[0-9.]+"', 'APP_VERSION: "1.9.1"', text)
template.write_text(text)
shutil.copyfile(root / "releases/v1.9.1/orders_submit_app.py", root / "src/orders_submit/app.py")
print("Applied v1.9.1: inventory call with 1 s client timeout, fail open; timeout default 10; version 1.9.1")
