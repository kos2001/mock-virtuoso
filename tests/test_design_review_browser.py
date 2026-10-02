"""Browser review flow with real ngspice; the optional bridge is not required."""
import os
from pathlib import Path
from urllib.parse import urlparse

import pytest

from mock_virtuoso.simulation import find_ngspice

pytestmark = pytest.mark.skipif(not os.environ.get('VERIFICATION_BROWSER') or not find_ngspice(),
                               reason='Requires Edge/Chromium and ngspice')


def test_review_dashboard_truth_pvt_stale_and_language(tmp_path, monkeypatch):
    from toolkit import circuit_service, review_service, verification_service
    playwright = pytest.importorskip('playwright.sync_api')
    root = Path.cwd()
    monkeypatch.setenv('NGSPICE_EXE', str(find_ngspice(root)))
    monkeypatch.setattr(review_service, 'ROOT', tmp_path)
    errors = []
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ['VERIFICATION_BROWSER'], headless=True)
        page = browser.new_page(viewport={'width':1400,'height':1000}, color_scheme='light')
        page.on('pageerror', lambda error: errors.append(str(error)))
        def respond(route):
            path = urlparse(route.request.url).path
            static = {'/':'floor/floor.html','/circuit.js':'floor/circuit.js','/verification.js':'floor/verification.js',
                      '/about.js':'toolkit/static/about.js','/render.js':'toolkit/static/render.js'}
            if path in static:
                return route.fulfill(body=(root/static[path]).read_bytes(), content_type='text/html' if path=='/' else 'application/javascript')
            actions = {'/api/circuit/catalog':circuit_service.catalog,'/api/circuit/check':circuit_service.inspect,
                       '/api/circuit/review':review_service.review,'/api/verification/catalog':verification_service.catalog}
            if path in actions:
                try:
                    result = actions[path]() if route.request.method=='GET' else actions[path](route.request.post_data_json)
                    return route.fulfill(json=result)
                except ValueError as exc:
                    return route.fulfill(status=400,json={'error':str(exc)})
            if path=='/api/feed':
                return route.fulfill(json={'seq':0,'lanes':{},'events':[],'ops':0,'cells':[]})
            return route.fulfill(json={'ok':True,'rows':[],'masters':{}})
        page.route('http://review.test/**',respond)
        page.goto('http://review.test/')
        page.locator('#circuit-open').click()
        page.locator('#circuit-cell-example').select_option('INV')
        page.locator('#circuit-cell-load').click()
        page.locator('#circuit-profile').select_option('generic')
        page.locator('#circuit-review-panel > summary').click()
        page.locator('#circuit-review-voltages').fill('1.62,1.8')
        page.locator('#circuit-review-run').click()
        playwright.expect(page.locator('#circuit-review-matrix tr')).to_have_count(2,timeout=60000)
        playwright.expect(page.locator('#circuit-dashboard-rows')).to_contain_text('통과')
        playwright.expect(page.locator('#circuit-dashboard-rows')).to_contain_text('미지원')
        page.locator('#circuit-review-matrix button').first.click()
        playwright.expect(page.locator('#circuit-review-truth tr')).to_have_count(2)
        playwright.expect(page.locator('#circuit-plot polyline')).not_to_have_count(0)
        page.locator('#circuit-review-power').fill('0.000001')
        playwright.expect(page.locator('#circuit-review-stale')).to_be_visible()
        playwright.expect(page.locator('#circuit-dashboard-rows')).to_contain_text('재검사 필요')
        page.locator('#circuit-review-run').click()
        playwright.expect(page.locator('#circuit-review-state')).to_contain_text('실패',timeout=60000)
        playwright.expect(page.locator('#circuit-review-stale')).to_be_hidden()
        page.locator('#circuit-panel [data-ui-language]').select_option('en')
        playwright.expect(page.locator('#circuit-dashboard')).to_contain_text('Unsupported')
        playwright.expect(page.locator('#circuit-review-panel')).to_contain_text('Maximum delay')
        # A physical report is a separate scope and becomes stale independently.
        page.evaluate("window.dispatchEvent(new CustomEvent('floor-verification-result',{detail:{report:{run_id:'a'.repeat(32),drc:{status:'pass'},lvs:{status:'not_run'}},stale:false}}))")
        playwright.expect(page.locator('#circuit-review-layout')).to_have_value('a'*32)
        page.evaluate("window.dispatchEvent(new CustomEvent('floor-verification-result',{detail:{report:{run_id:'a'.repeat(32),drc:{status:'pass'}},stale:true}}))")
        playwright.expect(page.locator('#circuit-dashboard')).to_contain_text('Rerun required')
        page.set_viewport_size({'width':390,'height':844})
        assert page.locator('#circuit-panel').evaluate('(el)=>el.scrollWidth<=el.clientWidth')
        assert not errors, errors
        browser.close()
