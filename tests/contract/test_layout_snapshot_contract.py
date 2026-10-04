import json


def test_snapshot_over_authenticated_bridge_is_readonly(bridge_client):
    client, session = bridge_client
    session.evaluate('cv = dbOpenCellViewByType("LIB" "CELL" "layout" "maskLayout" "a")')
    session.evaluate('dbCreateRect(cv list("met1" "drawing") list(0:0 2:1))')
    session.evaluate('dbClose(cv)')
    result = client.execute_skill('mockLayoutSnapshot("LIB" "CELL" "layout")')
    assert result.status.value == 'success', result.errors
    data = json.loads(result.output)
    if isinstance(data,str):
        data=json.loads(data)
    assert data['cells']['LIB/CELL/layout']['shapes'][0]['bBox'] == [[0,0],[2,1]]
    assert len(data['snapshot_sha256']) == 64
    assert session.evaluate('dbGetOpenCellViews()') == []
