import math

import pytest

from mock_virtuoso.circuit import example
from mock_virtuoso.simulation import find_ngspice, simulate


@pytest.fixture
def engine():
    exe = find_ngspice()
    if not exe or not exe.is_file():
        pytest.skip("Install ngspice or set NGSPICE_EXE for real circuit simulation tests")
    return exe


def run(c, engine, tmp_path):
    result = simulate(c, executable=engine, output=tmp_path)
    assert result["status"] == "pass", result.get("reason", result)
    assert "ngspice" in result["engine_version"]
    assert (tmp_path / result["run_id"] / "result.raw").is_file()
    return result["data"]


def column(data, name):
    return next(c for c in data["columns"] if c["name"] == name)


def test_real_operating_point_matches_voltage_divider(engine, tmp_path):
    data = run(example(), engine, tmp_path)
    assert column(data, "v(vout)")["real"][0] == pytest.approx(.5)
    assert column(data, "i(v_v1)")["real"][0] == pytest.approx(-.0005)


def test_real_dc_sweep_matches_analytic_transfer(engine, tmp_path):
    c = example()
    c["analysis"] = {"type": "dc", "source": "V1", "start": 0, "stop": 2, "step": .1}
    data = run(c, engine, tmp_path)
    assert data["sample_count"] == 21
    assert column(data, "v(vout)")["real"] == pytest.approx([i*.05 for i in range(21)])


def test_real_ac_rc_filter_preserves_complex_phase(engine, tmp_path):
    c = example()
    c["devices"][2] = {"kind": "C", "id": "C1", "nodes": ["vout", "0"], "value": 1e-6}
    c["analysis"] = {"type": "ac", "start": 10, "stop": 10000, "points": 10}
    data = run(c, engine, tmp_path)
    output = column(data, "v(vout)")
    for f, r, i in zip(column(data, "frequency")["real"], output["real"], output["imag"]):
        expected = 1/(1+2j*math.pi*f*.001)
        assert complex(r, i) == pytest.approx(expected, rel=1e-5)


def test_real_transient_matches_rc_time_constant(engine, tmp_path):
    c = example()
    c["devices"][0]["value"] = 0
    c["devices"][0]["pulse"] = {"low": 0, "high": 1, "delay": 1e-6,
                                    "rise": 1e-9, "fall": 1e-9, "width": .01, "period": .02}
    c["devices"][2] = {"kind": "C", "id": "C1", "nodes": ["vout", "0"], "value": 1e-6}
    c["analysis"] = {"type": "tran", "step": 1e-5, "stop": .005}
    data = run(c, engine, tmp_path)
    times = column(data, "time")["real"]
    idx = min(range(len(times)), key=lambda i: abs(times[i]-.001001))
    assert column(data, "v(vout)")["real"][idx] == pytest.approx(1-math.exp(-(times[idx]-1e-6)/.001), abs=.002)


def test_erc_blocks_before_any_engine_is_needed(tmp_path):
    c = example()
    c["devices"].pop()
    assert simulate(c, executable=tmp_path / "missing.exe", output=tmp_path)["status"] == "blocked"
    assert not list(tmp_path.iterdir())


def test_missing_engine_is_not_a_pass(tmp_path):
    assert simulate(example(), executable=tmp_path / "missing.exe", output=tmp_path)["status"] == "not_run"


def test_generic_diode_forward_bias(engine, tmp_path):
    c = example()
    c["devices"][2] = {"kind": "D", "id": "D1", "nodes": ["vout", "0"]}
    data = run(c, engine, tmp_path)
    assert .5 < column(data, "v(vout)")["real"][0] < .8


def test_generic_cmos_inverter_has_correct_dc_polarity(engine, tmp_path):
    c = {"name": "INVERTER", "devices": [
        {"id": "VDD", "kind": "V", "nodes": ["vdd", "0"], "value": 5},
        {"id": "VIN", "kind": "V", "nodes": ["vin", "0"], "value": 0},
        {"id": "MN", "kind": "NMOS", "nodes": ["vout", "vin", "0", "0"]},
        {"id": "MP", "kind": "PMOS", "nodes": ["vout", "vin", "vdd", "vdd"]}],
        "analysis": {"type": "dc", "source": "VIN", "start": 0, "stop": 5, "step": .5}}
    data = run(c, engine, tmp_path)
    values = column(data, "v(vout)")["real"]
    assert values[0] == pytest.approx(5, abs=.01)
    assert values[-1] == pytest.approx(0, abs=.01)


@pytest.mark.parametrize("failure", ["timeout", "corrupt_output", "nonzero_exit"])
def test_engine_failures_never_become_a_success(failure, tmp_path, monkeypatch):
    import subprocess
    from types import SimpleNamespace
    from mock_virtuoso import simulation
    exe = tmp_path / "test-engine"
    exe.touch()
    def invoke(command, **kwargs):
        if "-v" in command:
            return SimpleNamespace(stdout="test ngspice")
        if failure == "timeout":
            raise subprocess.TimeoutExpired(command, 30)
        if failure == "corrupt_output":
            (kwargs["cwd"] / "result.raw").write_text("incomplete output")
        return SimpleNamespace(returncode=1 if failure == "nonzero_exit" else 0)
    monkeypatch.setattr(simulation.subprocess, "run", invoke)
    result = simulate(example(), executable=exe, output=tmp_path / "runs")
    assert result["status"] == "error"
    assert "data" not in result
    assert result["reason"]
