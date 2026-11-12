import sqlite3
import pytest
from backend.store import Store


def quote(t, price, volume=100):
    return {"id": "AAPL", "time": t, "price": price, "day_volume": volume}


def test_duplicate_revision_and_receipt_order_replay(tmp_path):
    store = Store(tmp_path / "quotes.db")
    a = quote(100000, 10)
    b = quote(100000, 12)
    assert store.ingest(a, 100001) == (1, "new")
    assert store.ingest(a, 100002) == (2, "duplicate")
    assert store.ingest(b, 100003) == (3, "revised")
    assert store.ingest(a, 100004) == (4, "duplicate")
    assert store.candles(through=1)[0]["close"] == 10
    assert store.candles(through=2)[0]["close"] == 10
    assert store.candles(through=3)[0]["close"] == 12
    assert store.candles(through=4)[0]["close"] == 12
    assert store.stats()["revisions"] == 2
    assert store.stats()["duplicates"] == 2
    assert len(store.events()) == 4
    assert store.events()[2]["version"] == 2


def test_out_of_order_recomputes_open_close_and_volume(tmp_path):
    store = Store(tmp_path / "quotes.db")
    for msg in [quote(104000, 12, 130), quote(100000, 10, 100), quote(102000, 9, 110)]:
        store.ingest(msg, 104001)
    bar = store.candles(clock_ms=104999)[0]
    assert (bar["open"],bar["high"],bar["low"],bar["close"],bar["volume"]) == (10,12,9,12,30)
    assert bar["complete"] is False
    assert store.candles(clock_ms=105000)[0]["complete"] is True
    # A revision to an old point corrects price and downstream volume deltas.
    store.ingest(quote(102000, 15, 115), 106000)
    assert store.candles()[0]["high"] == 15
    assert store.candles()[0]["close"] == 12
    assert store.candles()[0]["volume"] == 30


def test_volume_reset_missing_value_and_symbol_isolation(tmp_path):
    store=Store(tmp_path / "quotes.db")
    for msg in [quote(100000,10,100),quote(101000,11,105),quote(102000,12,2),quote(103000,13,None),quote(104000,14,8)]:
        store.ingest(msg)
    store.ingest({"id":"BTC-USD","time":100000,"price":60000,"day_volume":9000000})
    bars=store.candles()
    assert bars[0]["volume"] == 5
    assert bars[1]["volume"] == 0


def test_persistence_and_completion_versions(tmp_path):
    path=tmp_path / "quotes.db"
    store=Store(path)
    store.ingest(quote(100000,10),100001)
    store.materialize(104999)
    store.materialize(104999)
    store.materialize(105000)
    assert store.stats()["candle_versions"] == 2
    store.db.close()
    restored=Store(path)
    assert restored.candles()[0]["close"] == 10
    assert [r[0] for r in restored.db.execute("SELECT complete FROM candle_versions ORDER BY version")] == [0,1]
    assert restored.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


@pytest.mark.parametrize('message',[quote(0,10),quote(1000,float('nan')),quote(1000,-1),quote(1000,10,-1)])
def test_invalid_observations_are_not_recorded(tmp_path,message):
    store=Store(tmp_path / "quotes.db")
    with pytest.raises(ValueError): store.ingest(message)
    assert store.stats()["receipts"] == 0
