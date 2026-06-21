"""Run G4beamline either inside the published Docker image or with a native g4bl.

The HFOFO MC is a black box: write an input card + include files into a working
directory, run ``g4bl``, read the detector files back. This module isolates all
of the awkward container/runtime details so the rest of the framework only deals
with "run this config dir, give me the output dir".

Docker recipe (discovered empirically against ghcr.io/lawrenceleejr/g4beamline):
  * ``--network none``           -- g4bldata otherwise blocks on a network poll
  * ``QT_QPA_PLATFORM=offscreen``-- g4bl links Qt even in batch mode
  * write a ``.data`` file pointing g4bl at the in-image Geant4 datasets, so it
    never launches the (headless-hanging) g4bldata GUI to "find" them.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field

DEFAULT_IMAGE = "ghcr.io/lawrenceleejr/g4beamline:main"
# Location of the Geant4 datasets inside the published image.
DEFAULT_G4DATA = (
    "/usr/local/share/geant4/install/4.11.0.2/share/Geant4-11.0.2/data"
)
# g4bl install dir inside the image (where the .data file must live).
DEFAULT_G4BL_DIR = "/opt/g4beamline/build"


@dataclass
class RunResult:
    success: bool
    returncode: int
    workdir: str
    wall_seconds: float
    log: str = ""


@dataclass
class G4blRunner:
    """Execute a g4bl input card and return the populated working directory.

    Parameters
    ----------
    backend : "docker" | "native"
    image : Docker image to use (docker backend).
    g4bl_bin : path to the g4bl binary (native backend).
    g4data_dir / g4bl_dir : in-image Geant4 data dir / g4bl install dir.
    timeout : per-run wall-clock limit in seconds.
    keep_workdir : if False the temp workdir is created under ``scratch_root``
        and left for the caller to clean up.
    """

    backend: str = "docker"
    image: str = DEFAULT_IMAGE
    g4bl_bin: str = "g4bl"
    g4data_dir: str = DEFAULT_G4DATA
    g4bl_dir: str = DEFAULT_G4BL_DIR
    timeout: float = 1800.0
    scratch_root: str | None = None
    env: dict = field(default_factory=dict)

    def make_workdir(self, config_dir, prefix="hfofo_"):
        """Copy a config directory into a fresh temp workdir and return its path."""
        workdir = tempfile.mkdtemp(prefix=prefix, dir=self.scratch_root)
        for name in os.listdir(config_dir):
            src = os.path.join(config_dir, name)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(workdir, name))
        return workdir

    def run(self, workdir, input_file="hfofo.in"):
        """Run g4bl on ``input_file`` inside ``workdir``. Returns a RunResult."""
        if self.backend == "docker":
            return self._run_docker(workdir, input_file)
        return self._run_native(workdir, input_file)

    # -- backends ------------------------------------------------------------

    def _run_docker(self, workdir, input_file):
        inner = (
            f'echo "{self.g4data_dir}" > "{self.g4bl_dir}/.data" && '
            f'"{self.g4bl_dir}/bin/g4bl" "{input_file}"'
        )
        cmd = [
            "docker", "run", "--rm", "--network", "none",
            "-e", "QT_QPA_PLATFORM=offscreen",
            "-v", f"{os.path.abspath(workdir)}:/work",
            "-w", "/work",
            self.image,
            "bash", "-lc", inner,
        ]
        return self._exec(cmd, workdir)

    def _run_native(self, workdir, input_file):
        env = os.environ.copy()
        env.setdefault("QT_QPA_PLATFORM", "offscreen")
        env.update(self.env)
        cmd = [self.g4bl_bin, input_file]
        return self._exec(cmd, workdir, env=env, cwd=workdir)

    def _exec(self, cmd, workdir, env=None, cwd=None):
        start = time.time()
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=self.timeout, env=env, cwd=cwd,
            )
            log = (proc.stdout or "") + (proc.stderr or "")
            ok = proc.returncode == 0 and "simulation complete" in log
            return RunResult(ok, proc.returncode, workdir, time.time() - start, log)
        except subprocess.TimeoutExpired as exc:
            log = (exc.stdout or "") + (exc.stderr or "") if exc.stdout else "timeout"
            return RunResult(False, 124, workdir, time.time() - start,
                             f"TIMEOUT after {self.timeout}s\n{log}")


def detect_backend():
    """Pick a sensible default backend: native g4bl if on PATH, else docker."""
    if shutil.which("g4bl"):
        return "native"
    return "docker"
