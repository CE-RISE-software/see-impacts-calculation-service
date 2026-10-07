import json
import os
import subprocess
import sys
from pathlib import Path


def test_synthetic_brightway_lcia(tmp_path):
    fixture = Path(__file__).parent / "fixtures" / "brightway_smoke.py"
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")}
    source = tmp_path / "approved-background"

    subprocess.run(
        [sys.executable, str(fixture), "build", str(tmp_path / "builder"), str(source)],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    calculation = subprocess.run(
        [sys.executable, str(fixture), "calculate", str(source), str(tmp_path / "workspace")],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(calculation.stdout.rsplit("\n", 2)[-2])
    assert result["score"] == 12.0
    assert result["unit"] == "kg CO2-eq"
    assert result["method"] == ["synthetic", "climate"]
