"""Apply the fictional v1.9.0 release (PR #214) to your working copy.

Makes exactly the two changes Northwind shipped:
  1. orders-submit now calls inventory-reserve before writing the order.
  2. The OrdersSubmitTimeout default drops from 10 to 3 seconds, and
     APP_VERSION becomes 1.9.0.
Run from the repository root:  python3 scripts/apply-v1.9.0.py
Then commit on a branch and open a pull request, as Chapter 4 describes.
"""
import pathlib
import shutil
import sys

root = pathlib.Path(__file__).resolve().parent.parent
template = root / "template.yaml"
text = template.read_text()

changes = [
    ("    Default: 10\n    MinValue: 1", "    Default: 3\n    MinValue: 1"),
    ('          APP_VERSION: "1.8.0"', '          APP_VERSION: "1.9.0"'),
]
for old, new in changes:
    if old not in text:
        sys.exit(f"Could not find expected text in template.yaml: {old!r}. Is v1.9.0 already applied?")
    text = text.replace(old, new)
template.write_text(text)

shutil.copyfile(root / "releases/v1.9.0/orders_submit_app.py", root / "src/orders_submit/app.py")
print("Applied v1.9.0: orders-submit calls inventory-reserve; timeout default 10 -> 3; version 1.9.0")
