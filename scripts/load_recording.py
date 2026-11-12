"""Load actual recorded Yahoo observations into a separate offline replay database."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.store import Store

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--database', default='data/replay.sqlite3')
parser.add_argument('--recording', default='docs/evidence/yahoo-recording.jsonl')
args = parser.parse_args()
store = Store(args.database)
if store.stats()['receipts']:
    parser.error('Use an empty database to preserve the supplied receipt order without mixing sessions.')
count = 0
for line in Path(args.recording).read_text().splitlines():
    record = json.loads(line)
    store.ingest(record['message'], record['receipt_ms'])
    count += 1
store.materialize()
print(f'Loaded {count} actual recorded Yahoo receipts into {args.database}. These are recordings, not a live feed.')
store.db.close()
