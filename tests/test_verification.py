"""Use KLayout's real report formats; no log-string pass detection."""
import pytest

db = pytest.importorskip("klayout.db")
rdb = pytest.importorskip("klayout.rdb")

from mock_virtuoso.verification import read_drc, read_lvs, run_verification


def test_drc_reads_real_marker_database(tmp_path):
    report = rdb.ReportDatabase("test")
    cell = report.create_cell("TOP")
    category = report.create_category("met1.width")
    path = tmp_path / "report.lyrdb"
    report.save(str(path))
    assert read_drc(path)["status"] == "pass"
    item = report.create_item(cell.rdb_id(), category.rdb_id())
    item.add_value(rdb.RdbItemValue(db.DBox(0, 0, 0.1, 1)))
    report.save(str(path))
    result = read_drc(path)
    assert result["status"] == "fail"
    assert result["violations"] == 1
    assert result["markers"][0]["category"] == "met1.width"
    assert result["markers"][0]["cell"] == "TOP"


def test_empty_lvs_database_never_passes(tmp_path):
    report = db.LayoutVsSchematic("TOP", 0.001)
    report.extract_netlist()
    path = tmp_path / "empty.lvsdb"
    report.write(str(path))
    assert read_lvs(path)["status"] == "fail"


def test_missing_top_is_rejected_before_execution(tmp_path):
    layout = db.Layout()
    cell = layout.create_cell("TOP")
    cell.shapes(layout.layer(68, 20)).insert(db.Box(0, 0, 100, 100))
    path = tmp_path / "in.gds"
    layout.write(str(path))
    with pytest.raises(ValueError, match="top cell"):
        run_verification(executable="unused", gds=path, top="MISSING",
                         decks=tmp_path, output=tmp_path)


@pytest.mark.parametrize("mismatch", [False, True])
def test_lvs_reads_actual_comparison_status(tmp_path, mismatch):
    layout = db.Layout()
    cell = layout.create_cell("TOP")
    index = layout.layer(1, 0)
    cell.shapes(index).insert(db.Box(0, 0, 100, 100))
    report = db.LayoutVsSchematic(db.RecursiveShapeIterator(layout, cell, []))
    metal = report.make_layer(index, "metal")
    report.connect(metal)
    report.extract_netlist()
    netlist = report.netlist()
    resistor = db.DeviceClassResistor()
    resistor.name = "RES"
    netlist.add(resistor)
    circuit = netlist.circuit_by_name("TOP")
    device = circuit.create_device(resistor, "R1")
    device.set_parameter("R", 100)
    device.connect_terminal("A", circuit.create_net("A"))
    device.connect_terminal("B", circuit.create_net("B"))
    reference = netlist.dup()
    if mismatch:
        next(reference.circuit_by_name("TOP").each_device()).set_parameter("R", 200)
    report.reference = reference
    report.compare(db.NetlistComparer())
    path = tmp_path / "result.lvsdb"
    report.write(str(path))
    result = read_lvs(path)
    assert result["status"] == ("fail" if mismatch else "pass")
    assert result["extracted_devices"] == 1


def test_upload_does_not_accept_file_paths_or_invalid_base64():
    from toolkit.verification_service import verify_upload
    with pytest.raises(ValueError, match="Unknown project settings"):
        verify_upload({"top": "TOP", "gds": "C:/some/file.gds"})
    with pytest.raises(ValueError, match="encoding"):
        verify_upload({"top": "TOP", "gds_base64": "!"})


def test_floor_http_screen_and_input_errors():
    import json
    import threading
    from http.server import ThreadingHTTPServer
    from urllib.error import HTTPError
    from urllib.request import Request, urlopen
    pytest.importorskip("virtuoso_bridge")
    from floor.design_floor import Handler

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urlopen(base + "/") as response:
            assert b"/verification.js" in response.read()
        with urlopen(base + "/verification.js") as response:
            assert b"/api/verification/inspect" in response.read()
        request = Request(base + "/api/verification", data=b"{}",
                          headers={"Content-Type": "application/json"})
        with pytest.raises(HTTPError) as caught:
            urlopen(request)
        assert caught.value.code == 400
        assert "top cell" in json.loads(caught.value.read())["error"]
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
