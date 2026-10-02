"""Exercise live language changes and the standard-cell waveform viewer."""
import os
from http.server import ThreadingHTTPServer
import threading

import pytest

from mock_virtuoso.simulation import find_ngspice


@pytest.mark.skipif(not os.environ.get('VERIFICATION_BROWSER') or not find_ngspice(), reason='Requires browser/ngspice')
def test_language_examples_and_waveform_controls(tmp_path,monkeypatch):
    pytest.importorskip('virtuoso_bridge')
    playwright=pytest.importorskip('playwright.sync_api')
    from floor import design_floor as floor
    from toolkit import circuit_service
    monkeypatch.setenv('NGSPICE_EXE',str(find_ngspice()))
    monkeypatch.setattr(circuit_service,'ROOT',tmp_path)
    server=ThreadingHTTPServer(('127.0.0.1',0),floor.Handler)
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    try:
        with playwright.sync_playwright() as p:
            browser=p.chromium.launch(executable_path=os.environ['VERIFICATION_BROWSER'],headless=True)
            page=browser.new_page(viewport={'width':1280,'height':960})
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(f'http://127.0.0.1:{server.server_port}/')
            page.locator('body>header [data-ui-language]').select_option('en')
            playwright.expect(page.locator('#circuit-open')).to_have_text('Circuit · Simulation')
            page.locator('#circuit-open').click()
            playwright.expect(page.locator('#circuit-cell-load')).to_be_enabled()
            page.locator('#circuit-cell-example').select_option('NAND2')
            page.locator('#circuit-cell-load').click()
            page.locator('#circuit-profile').select_option('generic')
            name=page.locator('#circuit-name').input_value()
            page.locator('#circuit-run').click()
            playwright.expect(page.locator('#circuit-status')).to_contain_text('Simulation complete',timeout=20000)
            playwright.expect(page.locator('#circuit-plot [data-trace]')).to_have_count(3)
            playwright.expect(page.locator('#circuit-probe')).to_contain_text('v(vout)')
            page.locator('#circuit-zoom-in').click()
            playwright.expect(page.locator('#circuit-range')).to_contain_text('2×')
            page.locator('#circuit-pan').evaluate("e=>{e.value='50';e.dispatchEvent(new Event('input',{bubbles:true}));}")
            page.locator('#circuit-cursor').evaluate("e=>{e.value=e.max;e.dispatchEvent(new Event('input',{bubbles:true}));}")
            assert float(page.locator('#circuit-cursor').input_value())>0
            page.locator('#circuit-panel [data-ui-language]').select_option('ko')
            playwright.expect(page.locator('#circuit-run')).to_have_text('시뮬레이션 실행')
            assert page.locator('#circuit-name').input_value()==name
            playwright.expect(page.locator('#circuit-plot [data-trace]')).to_have_count(3)
            page.locator('#circuit-panel [data-ui-language]').select_option('en')
            page.locator('#circuit-zoom-reset').click()
            playwright.expect(page.locator('#circuit-range')).to_contain_text('1×')
            page.locator('#circuit-plot').scroll_into_view_if_needed()
            page.screenshot(path=str(tmp_path/'waves-en.png'))
            page.set_viewport_size({'width':390,'height':844})
            assert page.locator('#circuit-panel').evaluate('e=>e.scrollWidth<=e.clientWidth')
            page.locator('#circuit-close').click()
            page.locator('#verify-open').click()
            playwright.expect(page.locator('#verify-title')).to_have_text('DRC / LVS · Physical verification')
            page.locator('#verify-top').fill('my_cell_01')
            page.locator('#verification-panel [data-ui-language]').select_option('ko')
            playwright.expect(page.locator('#verify-title')).to_have_text('DRC / LVS · 물리 검증')
            assert page.locator('#verify-top').input_value()=='my_cell_01'
            page.locator('#verification-panel [data-ui-language]').select_option('en')
            page.reload()
            playwright.expect(page.locator('html')).to_have_attribute('lang','en')
            page.locator('#circuit-open').click()
            playwright.expect(page.locator('#circuit-name')).to_have_value(name)
            assert not errors,errors
            browser.close()
    finally:
        server.shutdown();server.server_close();worker.join()
