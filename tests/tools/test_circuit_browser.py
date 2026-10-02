"""Exercise the integrated editor against the real floor HTTP handler and ngspice."""
import json
import os
from pathlib import Path
from http.server import ThreadingHTTPServer
import threading

import pytest

from mock_virtuoso.simulation import find_ngspice


@pytest.mark.skipif(not os.environ.get("VERIFICATION_BROWSER") or not find_ngspice(),
                    reason="Requires a headless browser and real ngspice")
def test_edit_check_simulate_save_and_restore_in_same_floor(tmp_path, monkeypatch):
    playwright = pytest.importorskip("playwright.sync_api")
    pytest.importorskip("virtuoso_bridge")
    from floor import design_floor as floor
    from toolkit import circuit_service
    from mock_virtuoso.server import MockVirtuosoServer
    from mock_virtuoso.session import Session
    from mock_virtuoso.bridge_compat import match_client_auth
    from virtuoso_bridge import VirtuosoClient

    executable = find_ngspice()
    monkeypatch.setenv("NGSPICE_EXE", str(executable))
    monkeypatch.setattr(circuit_service, "ROOT", tmp_path)
    mock = MockVirtuosoServer(Session(artifact_dir=tmp_path))
    client = VirtuosoClient.local(port=mock.port)
    match_client_auth(mock, client)
    mock.start()
    monkeypatch.setattr(floor, "REQUEST_CLIENT", client)
    server = ThreadingHTTPServer(("127.0.0.1", 0), floor.Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    errors = []
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(executable_path=os.environ["VERIFICATION_BROWSER"], headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 960})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{server.server_port}/")
            page.locator("#circuit-open").click()
            playwright.expect(page.locator("#circuit-engine")).to_contain_text("준비됨")
            playwright.expect(page.locator("#circuit-file")).to_be_hidden()
            page.locator("#circuit-run").click()
            playwright.expect(page.locator("#circuit-status")).to_contain_text("해석 완료", timeout=15000)
            playwright.expect(page.locator("#circuit-values")).to_contain_text("0.500000")
            page.locator("#circuit-save").click()
            playwright.expect(page.locator("#circuit-status")).to_contain_text("저장했습니다")
            # Change an actual resistance, then restore the same shared DB cell.
            page.locator('.device[data-index="1"] input[type="number"]').fill("2000")
            page.locator("#circuit-load").click()
            playwright.expect(page.locator('.device[data-index="1"] input[type="number"]')).to_have_value("1000")
            page.locator("#circuit-analysis").select_option("dc")
            page.locator("#circuit-run").click()
            playwright.expect(page.locator("#circuit-wave")).to_be_visible(timeout=15000)
            playwright.expect(page.locator("#circuit-range")).to_contain_text("21 samples")
            with page.expect_download() as download:
                page.locator("#circuit-report").click()
            report = json.loads(Path(download.value.path()).read_text())
            assert report["status"] == "pass"
            assert report["data"]["sample_count"] == 21
            page.locator("#circuit-analysis").select_option("op")
            page.get_by_text("실험 관리 · corners / 온도 / sweep / 합격 기준", exact=True).click()
            page.locator("#circuit-sweep-device").fill("V1")
            page.locator("#circuit-sweep-values").fill("1,2")
            page.locator("#circuit-experiment").click()
            playwright.expect(page.locator("#circuit-status")).to_contain_text("실험 fail", timeout=20000)
            playwright.expect(page.locator("#circuit-matrix tr")).to_have_count(2)
            page.locator("#circuit-history").click()
            playwright.expect(page.locator("#circuit-history-result")).to_contain_text("DIVIDER")
            with page.expect_download() as exported:
                page.locator("#circuit-experiment-export").click()
            experiment = json.loads(Path(exported.value.path()).read_text())
            assert [r["status"] for r in experiment["runs"]] == ["pass", "fail"]
            page.locator("#circuit-analysis").select_option("dc")
            page.screenshot(path=str(tmp_path / "circuit-desktop.png"), full_page=True)
            url = page.url
            page.locator("#circuit-close").click()
            playwright.expect(page.locator("#cv")).to_be_visible()
            assert page.url == url
            page.reload()
            page.locator("#circuit-open").click()
            playwright.expect(page.locator("#circuit-analysis")).to_have_value("dc")
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.locator("#circuit-panel").evaluate("e=>e.scrollWidth<=e.clientWidth")
            page.screenshot(path=str(tmp_path / "circuit-mobile.png"), full_page=True)
            assert not errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
        mock.stop()
