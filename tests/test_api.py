from fastapi.testclient import TestClient
from backend.main import create_app


def test_websocket_database_chart_contract_and_failure(tmp_path):
    app=create_app(tmp_path / "market.db",live=False)
    with TestClient(app) as client:
        # Synthetic fixtures test the integration contract, never claimed as live Yahoo evidence.
        app.state.store.ingest({"id":"AAPL","time":100000,"price":10,"day_volume":100},100001)
        app.state.store.ingest({"id":"AAPL","time":102000,"price":12,"day_volume":120},102001)
        with client.websocket_connect('/ws') as ws:
            packet=ws.receive_json()
            assert packet['candles'][0]['close'] == 12
            assert packet['candles'][0]['volume'] == 20
            assert packet['stats']['receipts'] == 2
            ws.send_json({'action':'disconnect'})
            assert ws.receive_json()['feed']['state'] == 'unavailable'
            ws.send_json({'action':'replay'})
            packet=ws.receive_json()
            assert packet['mode'] == 'replay'
            assert packet['candles'] == []
            packet=ws.receive_json()
            assert packet['cursor'] == 1
            assert packet['candles'][0]['close'] == 10
            packet=ws.receive_json()
            assert packet['replay_finished'] is True
            assert packet['candles'][0]['close'] == 12
        assert len(client.get('/api/observations').json()) == 2
        assert client.get('/api/candles?through=1').json()['candles'][0]['close'] == 10
        assert client.get('/api/observations?limit=1001').status_code == 422


def test_rejects_cross_site_control_channel(tmp_path):
    app=create_app(tmp_path / "market.db",live=False)
    from starlette.websockets import WebSocketDisconnect
    import pytest
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect('/ws',headers={'origin':'https://example.com'}): pass
