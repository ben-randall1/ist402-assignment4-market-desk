"""Event journal and deterministic source-time candle projection."""
import hashlib
import json
import math
import sqlite3
import time
from pathlib import Path

SOURCE = "Yahoo Finance WebSocket"


def normalize(message):
    symbol = str(message.get("id", ""))
    price = float(message["price"])
    stamp = int(message["time"])
    if not symbol or not math.isfinite(price) or price <= 0 or stamp <= 0:
        raise ValueError("Invalid quote")
    # Yahoo's protobuf time is milliseconds since Unix epoch.
    volume = message.get("day_volume")
    volume = None if volume is None else int(volume)
    if volume is not None and volume < 0:
        raise ValueError("Invalid cumulative volume")
    return {"symbol": symbol, "source_ms": stamp, "price": price, "day_volume": volume}


def project(events, interval=5, clock_ms=None):
    """Last distinct revision received wins; duplicate receipts never roll back state."""
    latest = {}
    seen = set()
    for event in events:
        if event["revision_id"] in seen:
            continue
        seen.add(event["revision_id"])
        latest[(event["symbol"], event["source_ms"])] = event
    candles = {}
    previous = {}
    clock_ms = int(time.time() * 1000) if clock_ms is None else clock_ms
    for event in sorted(latest.values(), key=lambda e: (e["symbol"], e["source_ms"])):
        symbol = event["symbol"]
        bucket = event["source_ms"] // (interval * 1000) * interval
        key = (symbol, bucket)
        price = event["price"]
        old = previous.get(symbol)
        volume = event["day_volume"]
        delta = 0
        # First observation, missing volume, session reset, and day boundaries have no baseline.
        if old and volume is not None and old["day_volume"] is not None:
            if old["source_ms"] // 86400000 == event["source_ms"] // 86400000:
                delta = max(0, volume - old["day_volume"])
        previous[symbol] = event
        if key not in candles:
            candles[key] = {"symbol": symbol, "time": bucket, "open": price,
                            "high": price, "low": price, "close": price, "volume": 0,
                            "complete": (bucket + interval) * 1000 <= clock_ms,
                            "source_ms": event["source_ms"], "receipt_ms": event["receipt_ms"],
                            "observations": 0}
        bar = candles[key]
        bar.update(high=max(bar["high"], price), low=min(bar["low"], price), close=price,
                   source_ms=event["source_ms"], receipt_ms=max(bar["receipt_ms"], event["receipt_ms"]))
        bar["volume"] += delta
        bar["observations"] += 1
    return list(candles.values())


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS revisions (
          id INTEGER PRIMARY KEY, symbol TEXT NOT NULL, source_ms INTEGER NOT NULL,
          source TEXT NOT NULL, version INTEGER NOT NULL, fingerprint TEXT NOT NULL,
          price REAL NOT NULL, day_volume INTEGER, raw_json TEXT NOT NULL,
          UNIQUE(symbol,source_ms,fingerprint), UNIQUE(symbol,source_ms,version));
        CREATE TABLE IF NOT EXISTS receipts (
          id INTEGER PRIMARY KEY, revision_id INTEGER NOT NULL REFERENCES revisions(id),
          receipt_ms INTEGER NOT NULL, disposition TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS revision_time ON revisions(symbol,source_ms);
        CREATE TABLE IF NOT EXISTS candle_versions (
          id INTEGER PRIMARY KEY, symbol TEXT NOT NULL, start_s INTEGER NOT NULL,
          interval_s INTEGER NOT NULL, version INTEGER NOT NULL, complete INTEGER NOT NULL,
          recorded_ms INTEGER NOT NULL, candle_json TEXT NOT NULL,
          UNIQUE(symbol,start_s,interval_s,version));
        """)
        self.db.commit()

    def ingest(self, message, receipt_ms=None):
        quote = normalize(message)
        receipt_ms = int(time.time() * 1000) if receipt_ms is None else receipt_ms
        payload = json.dumps(quote, sort_keys=True)
        fingerprint = hashlib.sha256(payload.encode()).hexdigest()
        key = (quote["symbol"], quote["source_ms"])
        with self.db:
            old = self.db.execute("SELECT id FROM revisions WHERE symbol=? AND source_ms=? AND fingerprint=?", (*key, fingerprint)).fetchone()
            version = self.db.execute("SELECT COALESCE(MAX(version),0) FROM revisions WHERE symbol=? AND source_ms=?", key).fetchone()[0] + 1
            if old:
                revision_id, disposition = old[0], "duplicate"
            else:
                disposition = "revised" if version > 1 else "new"
                cur = self.db.execute("INSERT INTO revisions(symbol,source_ms,source,version,fingerprint,price,day_volume,raw_json) VALUES(?,?,?,?,?,?,?,?)",
                                      (*key, SOURCE, version, fingerprint, quote["price"], quote["day_volume"], json.dumps(message, sort_keys=True)))
                revision_id = cur.lastrowid
            cur = self.db.execute("INSERT INTO receipts(revision_id,receipt_ms,disposition) VALUES(?,?,?)", (revision_id, receipt_ms, disposition))
        return cur.lastrowid, disposition

    def events(self, through=None):
        query = """SELECT r.*, r.id AS revision_id, e.id AS receipt_id, e.receipt_ms, e.disposition
                   FROM receipts e JOIN revisions r ON r.id=e.revision_id"""
        args = ()
        if through is not None:
            query += " WHERE e.id<=?"
            args = (through,)
        return [dict(row) for row in self.db.execute(query + " ORDER BY e.id", args)]

    def candles(self, interval=5, through=None, clock_ms=None):
        return project(self.events(through), interval, clock_ms)

    def materialize(self, clock_ms=None):
        now = int(time.time()*1000) if clock_ms is None else clock_ms
        with self.db:
            for candle in self.candles(clock_ms=now):
                key = (candle["symbol"], candle["time"], 5)
                encoded = json.dumps(candle, sort_keys=True)
                old = self.db.execute("SELECT version,candle_json FROM candle_versions WHERE symbol=? AND start_s=? AND interval_s=? ORDER BY version DESC LIMIT 1", key).fetchone()
                if old is None or old[1] != encoded:
                    self.db.execute("INSERT INTO candle_versions(symbol,start_s,interval_s,version,complete,recorded_ms,candle_json) VALUES(?,?,?,?,?,?,?)",
                                    (*key, 1 if old is None else old[0]+1, int(candle["complete"]), now, encoded))

    def stats(self):
        return {"observations": self.db.execute("SELECT COUNT(DISTINCT symbol || ':' || source_ms) FROM revisions").fetchone()[0],
                "revisions": self.db.execute("SELECT COUNT(*) FROM revisions").fetchone()[0],
                "receipts": self.db.execute("SELECT COUNT(*) FROM receipts").fetchone()[0],
                "duplicates": self.db.execute("SELECT COUNT(*) FROM receipts WHERE disposition='duplicate'").fetchone()[0],
                "candle_versions": self.db.execute("SELECT COUNT(*) FROM candle_versions").fetchone()[0]}
