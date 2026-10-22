"""Check release metadata and byte-for-byte source provenance without installing."""
from configparser import ConfigParser
from email.parser import BytesParser
from pathlib import Path
import tarfile
import tomllib
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
version = project["version"]
stem = f"endstone_antiphantom-{version}"
wheel = ROOT / "dist" / f"{stem}-py3-none-any.whl"
sdist = ROOT / "dist" / f"{stem}.tar.gz"
assert sorted(p.name for p in (ROOT / "dist").glob("*.whl")) == [wheel.name]
assert sorted(p.name for p in (ROOT / "dist").glob("*.tar.gz")) == [sdist.name]

with ZipFile(wheel) as archive:
    info = f"{stem}.dist-info"
    metadata = BytesParser().parsebytes(archive.read(f"{info}/METADATA"))
    assert metadata["Name"] == project["name"]
    assert metadata["Version"] == version
    assert set(metadata["Requires-Python"].split(",")) == {">=3.11", "<3.16"}
    assert all("extra == 'test'" in value or 'extra == "test"' in value
               for value in metadata.get_all("Requires-Dist", []))
    tags = BytesParser().parsebytes(archive.read(f"{info}/WHEEL"))
    assert tags["Root-Is-Purelib"] == "true"
    assert tags.get_all("Tag") == ["py3-none-any"]
    entries = ConfigParser()
    entries.read_string(archive.read(f"{info}/entry_points.txt").decode())
    assert dict(entries["endstone"]) == {"antiphantom": "endstone_antiphantom:AntiPhantom"}
    expected = {str(p.relative_to(ROOT / "src")): p.read_bytes()
                for p in (ROOT / "src" / "endstone_antiphantom").glob("*.py")}
    packaged = {name: archive.read(name) for name in archive.namelist()
                if name.startswith("endstone_antiphantom/")}
    assert packaged == expected, "Wheel sources differ from checkout"

with tarfile.open(sdist) as archive:
    for path in [ROOT / "pyproject.toml", ROOT / "README.md", *sorted((ROOT / "src").rglob("*.py"))]:
        member = archive.extractfile(f"{stem}/{path.relative_to(ROOT)}")
        assert member is not None and member.read() == path.read_bytes(), path

print(f"Verified {wheel.name} and {sdist.name}: metadata, entry point, and checkout sources")
