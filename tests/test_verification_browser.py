"""Optional headless browser test using real GDS/SPICE and KLayout runs."""
import json
import os
from pathlib import Path
from urllib.parse import urlparse

import pytest

pytestmark = pytest.mark.skipif(not os.environ.get("VERIFICATION_BROWSER") or not os.environ.get("KLAYOUT_EXE"),
                               reason="Set VERIFICATION_BROWSER and KLAYOUT_EXE for the browser integration test")


def test_settings_upload_export_and_project_rule_result(tmp_path, monkeypatch):
    playwright = pytest.importorskip("playwright.sync_api")
    from toolkit import verification_service
    from toolkit import circuit_service

    root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("SKY130_DECKS", str(root / ".tools/sky130"))
    monkeypatch.setattr(verification_service, "ROOT", tmp_path)
    errors = []
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ["VERIFICATION_BROWSER"], headless=True)
        page = browser.new_page(viewport={"width": 1200, "height": 950})
        page.on("pageerror", lambda error: errors.append(str(error)))
        # Isolate the optional bridge transport; run the real verification service.
        def respond(route):
            path = urlparse(route.request.url).path
            static = {"/": "floor/floor.html", "/verification.js": "floor/verification.js",
                      "/circuit.js": "floor/circuit.js",
                      "/render.js": "toolkit/static/render.js", "/about.js": "toolkit/static/about.js",
                      "/favicon.svg": "assets/icon-small.svg"}
            if path in static:
                mime = "text/html" if path == "/" else "application/javascript" if path.endswith(".js") else "image/svg+xml"
                return route.fulfill(body=(root / static[path]).read_bytes(), content_type=mime)
            actions = {"/api/verification/catalog": verification_service.catalog,
                       "/api/circuit/catalog": circuit_service.catalog,
                       "/api/circuit/check": circuit_service.inspect,
                       "/api/verification/inspect": verification_service.inspect_upload,
                       "/api/verification/settings": verification_service.validate_settings,
                       "/api/verification": verification_service.verify_upload}
            if path in actions:
                action = actions[path]
                value = action() if route.request.method == "GET" else action(route.request.post_data_json)
                return route.fulfill(json=value)
            # No design is attached in this component integration test.
            if path == "/api/feed":
                return route.fulfill(json={"seq": 0, "lanes": {}, "events": [], "ops": 0})
            return route.fulfill(json={"ok": True, "rows": [], "masters": {}})
        page.route("http://floor.test/**", respond)
        page.goto("http://floor.test/")
        page.locator("#verify-open").click()
        playwright.expect(page.locator("#verify-settingsFile")).to_be_hidden()
        playwright.expect(page.locator("#verify-deckState")).to_contain_text("준비됨")
        playwright.expect(page.locator("#verify-go")).to_be_disabled()
        playwright.expect(page.locator("#verify-readiness")).to_contain_text("SPICE 없음")
        fixture = root / ".tools/sky130-fixture"
        page.locator("#verify-gds").set_input_files(fixture / "sky130_fd_sc_hd__inv_1.gds")
        playwright.expect(page.locator("#verify-top")).to_have_value("sky130_fd_sc_hd__inv_1")
        page.locator("#verify-spice").set_input_files(fixture / "sky130_fd_sc_hd__inv_1.spice")
        playwright.expect(page.locator("#verify-substrate")).to_have_value("VNB")
        page.locator("#verify-addRule").click()
        with page.expect_download() as download:
            page.locator("#verify-export").click()
        config = json.loads(Path(download.value.path()).read_text())
        assert config["project_constraints"]["rules"][0]["layer"] == 68
        assert config["top"] == "sky130_fd_sc_hd__inv_1"
        assert "gds_base64" not in config
        page.locator("#verify-maxWidth").fill("0.1")
        page.locator("#verify-go").click()
        playwright.expect(page.locator("#verify-result")).to_be_visible(timeout=60000)
        playwright.expect(page.locator("#verify-gate")).to_contain_text("project_rules")
        failed = json.loads(page.locator("#verify-detail").text_content())
        assert failed["drc"]["status"] == failed["lvs"]["status"] == "pass"
        assert failed["project_rules"]["status"] == "fail"
        assert failed["drc_lvs_passed"] is True
        assert failed["checks_passed"] is False
        config_path = tmp_path / "profile.json"
        config_path.write_text(json.dumps(config))
        page.locator("#verify-settingsFile").set_input_files(config_path)
        playwright.expect(page.locator("#verify-maxWidth")).to_have_value("")
        page.locator("#verify-go").click()
        playwright.expect(page.locator("#verify-gate")).to_contain_text("준비 완료", timeout=60000)
        passed = json.loads(page.locator("#verify-detail").text_content())
        assert passed["project_rules"]["status"] == "pass"
        playwright.expect(page.locator('#verify-summary article[data-status="pass"]')).to_have_count(2)
        playwright.expect(page.locator('#verify-circuits')).to_contain_text('Match')
        playwright.expect(page.locator('#verify-provenance')).to_contain_text(passed['inputs']['gds']['sha256'])
        playwright.expect(page.locator('#verify-stale')).to_be_hidden()
        # Real geometry and netlist errors must be actionable outside the raw JSON.
        import klayout.db as db
        layout = db.Layout()
        layout.read(str(fixture / 'sky130_fd_sc_hd__inv_1.gds'))
        layout.top_cell().shapes(layout.layer(68, 20)).insert(db.DBox(10, 10, 10.05, 11))
        bad_gds = tmp_path / 'narrow.gds'
        layout.write(str(bad_gds))
        bad_spice = tmp_path / 'wrong.spice'
        source = (fixture / 'sky130_fd_sc_hd__inv_1.spice').read_text()
        assert '650000u' in source
        bad_spice.write_text(source.replace('650000u', '750000u'))
        page.locator('#verify-gds').set_input_files(bad_gds)
        playwright.expect(page.locator('#verify-stale')).to_be_visible()
        page.locator('#verify-spice').set_input_files(bad_spice)
        page.locator('#verify-go').click()
        playwright.expect(page.locator('#verify-summary article[data-status="fail"]')).to_have_count(2, timeout=60000)
        playwright.expect(page.locator('#verify-stale')).to_be_hidden()
        assert page.locator('#verify-markers tr').count() > 0
        playwright.expect(page.locator('#verify-markers')).to_contain_text('10')
        page.locator('#verify-markerFilter').fill('no-such-rule')
        playwright.expect(page.locator('#verify-markers tr')).to_have_count(0)
        page.locator('#verify-markerFilter').fill('10')
        assert page.locator('#verify-markers tr').count() > 0
        page.locator('#verification-panel [data-ui-language]').select_option('en')
        playwright.expect(page.locator('#verify-markerCount')).to_contain_text('Total violations')
        playwright.expect(page.locator('#verify-summary')).to_contain_text('fix the layout')
        page.locator('#verification-panel [data-ui-language]').select_option('ko')
        # DRC-only runs remain explicitly blocked by the missing LVS reference.
        page.locator('#verify-gds').set_input_files(fixture / 'sky130_fd_sc_hd__inv_1.gds')
        page.locator('#verify-spice').set_input_files([])
        playwright.expect(page.locator('#verify-readiness')).to_contain_text('SPICE 없음')
        page.locator('#verify-go').click()
        playwright.expect(page.locator('#verify-summary article[data-status="not_run"]')).to_have_count(1, timeout=60000)
        playwright.expect(page.locator('#verify-gate')).to_contain_text('lvs')
        playwright.expect(page.locator('#verify-circuits')).to_contain_text('비교된 회로가 없습니다')
        page.screenshot(path=str(tmp_path / "verification-desktop.png"), full_page=True)
        original_url = page.url
        page.locator("#verify-close").click()
        playwright.expect(page.locator("#cv")).to_be_visible()
        playwright.expect(page.locator("#go")).to_have_text("생성")
        page.locator("#verify-open").click()
        assert page.url == original_url
        playwright.expect(page.locator("#verify-top")).to_have_value("sky130_fd_sc_hd__inv_1")
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.getElementById('verification-panel').getBoundingClientRect().right <= window.innerWidth")
        assert page.locator('#verification-panel').evaluate('(el) => el.scrollWidth <= el.clientWidth')
        page.reload()
        page.locator("#verify-open").click()
        playwright.expect(page.locator("#verify-settingsState")).to_contain_text("복원")
        assert page.locator("#verify-rules .rule").count() == 1
        page.screenshot(path=str(tmp_path / "verification-mobile.png"), full_page=True)
        assert not errors
        browser.close()
