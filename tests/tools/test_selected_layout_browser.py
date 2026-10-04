"""Live HTTP/bridge/GDS UI test; no user's running design is touched."""
import json
import os
from http.server import ThreadingHTTPServer
import threading

import pytest


@pytest.mark.skipif(not os.environ.get('VERIFICATION_BROWSER'), reason='Requires test browser')
def test_selected_cell_check_and_master_staleness(tmp_path, monkeypatch):
    pytest.importorskip('klayout.db')
    playwright = pytest.importorskip('playwright.sync_api')
    from virtuoso_bridge import VirtuosoClient
    from mock_virtuoso.bridge_compat import match_client_auth
    from mock_virtuoso.session import Session
    from mock_virtuoso.server import MockVirtuosoServer
    from floor import design_floor as floor
    from toolkit import layout_verification

    session = Session(artifact_dir=tmp_path)
    mock = MockVirtuosoServer(session)
    client = VirtuosoClient.local(port=mock.port)
    match_client_auth(mock,client)
    mock.start()
    source = ('m = dbOpenCellViewByType("LIB" "MASTER" "layout" "maskLayout" "a") '
              'dbCreateRect(m list("met1" "drawing") list(0:0 2:1)) '
              'cv = dbOpenCellViewByType("LIB" "TOP" "layout" "maskLayout" "a") '
              'dbCreateInst(cv m "I0" 0:0 "R90")')
    assert client.execute_skill(source).status.value == 'success'
    transcript=floor.Transcript(); transcript.record('request',source,bytes([2]),1)
    monkeypatch.setattr(floor,'READER',client)
    monkeypatch.setattr(floor,'REQUEST_CLIENT',client)
    monkeypatch.setattr(floor,'TRANSCRIPT',transcript)
    monkeypatch.setattr(layout_verification,'ROOT',tmp_path)
    server=ThreadingHTTPServer(('127.0.0.1',0),floor.Handler)
    worker=threading.Thread(target=server.serve_forever,daemon=True); worker.start()
    try:
        with playwright.sync_playwright() as p:
            browser=p.chromium.launch(executable_path=os.environ['VERIFICATION_BROWSER'],headless=True)
            page=browser.new_page(viewport={'width':1280,'height':960})
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(f'http://127.0.0.1:{server.server_port}/')
            playwright.expect(page.locator('#layout-cell option[value="LIB/TOP"]')).to_have_count(1)
            page.locator('#layout-cell').select_option('LIB/TOP')
            page.locator('#layout-check-open').click()
            page.locator('#layout-check-run').click()
            playwright.expect(page.locator('#layout-check-result')).to_be_visible(timeout=20000)
            playwright.expect(page.locator('#layout-check-summary')).to_contain_text('GDS 형상·계층 재읽기: 통과')
            playwright.expect(page.locator('#layout-check-summary')).to_contain_text('PDK DRC: 미실행')
            playwright.expect(page.locator('#layout-check-stale')).to_be_hidden()
            report=json.loads(page.locator('#layout-check-detail').text_content())
            assert report['target']['cell']=='TOP' and report['counts']['cellviews']==2
            with page.expect_download() as download:
                page.locator('#layout-check-json').click()
            assert json.loads(open(download.value.path()).read())['snapshot_sha256']==report['snapshot_sha256']
            page.screenshot(path=str(tmp_path/'selected-layout.png'))
            page.set_viewport_size({'width':390,'height':844})
            assert page.locator('#layout-check-panel').evaluate('e=>e.scrollWidth<=e.clientWidth')
            page.screenshot(path=str(tmp_path/'selected-layout-mobile.png'))
            assert client.execute_skill('dbCreateRect(m list("met2" "drawing") list(3:0 4:1))').status.value=='success'
            playwright.expect(page.locator('#layout-check-stale')).to_be_visible(timeout=10000)
            page.locator('#layout-check-run').click()
            playwright.expect(page.locator('#layout-check-stale')).to_be_hidden(timeout=10000)
            page.locator('#layout-check-profile').select_option('sky130')
            playwright.expect(page.locator('#layout-check-physical')).to_be_visible()
            playwright.expect(page.locator('#layout-check-stale')).to_be_visible()
            assert not errors, errors
            browser.close()
    finally:
        server.shutdown();server.server_close();worker.join();mock.stop()
