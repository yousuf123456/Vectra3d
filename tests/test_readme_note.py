"""The students' "Read me first" note shipped beside Vectra3D.exe (G6.2).

Two first-run hurdles look like a broken app to a student who has not been
told: Windows SmartScreen on the unsigned .exe, and the slow first launch
while the app prepares itself. The note is the only place they are told, so
these check it still says so, and that the build still ships it.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGING = ROOT / "packaging"
NOTE = PACKAGING / "Read me first.txt"
INSTALLER = PACKAGING / "vectra3d.iss"
VERSION = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
    "project"
]["version"]


def test_the_note_tells_students_how_to_get_past_smartscreen() -> None:
    text = NOTE.read_text(encoding="utf-8")
    assert "Windows protected your PC" in text
    assert '"More info"' in text and '"Run anyway"' in text


def test_the_note_warns_that_starting_takes_a_while() -> None:
    text = NOTE.read_text(encoding="utf-8")
    assert "Starting takes a while" in text
    assert "first launch can take a minute" in text


def test_the_note_names_the_setup_file_of_this_version() -> None:
    assert f"Vectra3D-{VERSION}-setup.exe" in NOTE.read_text(encoding="utf-8")


def test_the_note_is_plain_ascii_so_notepad_shows_it_right() -> None:
    NOTE.read_bytes().decode("ascii")


def test_the_build_copies_the_note_beside_the_exe() -> None:
    spec = (PACKAGING / "vectra3d.spec").read_text(encoding="utf-8")
    assert f'README_NAME = "{NOTE.name}"' in spec
    assert 'os.path.join(DISTPATH, "Vectra3D", README_NAME)' in spec


# --- The installer (G6.1b) ---


def test_the_installer_has_the_projects_version() -> None:
    assert f'#define AppVersion "{VERSION}"' in INSTALLER.read_text(encoding="utf-8")


def test_the_installer_needs_no_administrator() -> None:
    assert "PrivilegesRequired=lowest" in INSTALLER.read_text(encoding="utf-8")


def test_the_installer_ships_the_whole_build_folder_and_the_note() -> None:
    script = INSTALLER.read_text(encoding="utf-8")
    # The .exe cannot run without its _internal folder beside it.
    assert r'Source: "..\dist\{#AppName}\*"' in script
    assert "recursesubdirs" in script
    assert f'#define ReadMe "{NOTE.name}"' in script
