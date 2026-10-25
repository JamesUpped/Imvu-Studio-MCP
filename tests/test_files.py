from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image

from imvu_studio_mcp.config import Settings, scoped_path
from imvu_studio_mcp.projects import inspect_project, list_projects
from imvu_studio_mcp.textures import TextureService, image_info


def test_inventory_preserves_ids_and_filters_private_metadata(workspace):
    settings, draft, target, source = workspace
    result = list_projects(settings)
    assert result["count"] == 1
    inspection = inspect_project(settings, str(draft))
    assert inspection["metadata"] == {"draft_properties.json": {"ProductName": "Test garment"}}
    assert inspection["assets"][0]["relative_path"] == "diffuse.png"
    assert inspection["index_components"][1]["attributes"]["ID"] == "7"
    assert inspection["index_components"][2]["children"][0]["attributes"]["ID"] == "41"


def test_xml_external_entities_are_rejected(workspace):
    settings, draft, *_ = workspace
    (draft / "index.xml").write_text('<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><x>&e;</x>')
    with pytest.raises(Exception, match="EntitiesForbidden"):
        inspect_project(settings, str(draft))


def test_scopes_and_hidden_files(workspace, tmp_path):
    settings, draft, target, source = workspace
    outside = tmp_path / "outside.png"
    Image.new("RGB", (1, 1)).save(outside)
    for path in (str(outside), str(draft / ".." / ".." / ".." / "outside.png")):
        with pytest.raises(ValueError, match="outside"):
            TextureService(settings).inspect(path)
    with pytest.raises(ValueError, match="absolute"):
        scoped_path("diffuse.png", settings.project_roots)
    hidden = draft / ".private"
    hidden.mkdir()
    copy = hidden / "copy.png"
    copy.write_bytes(target.read_bytes())
    with pytest.raises(ValueError, match="Hidden"):
        TextureService(settings).inspect(str(copy))


def test_symlink_escape(workspace, tmp_path):
    settings, draft, target, source = workspace
    outside = tmp_path / "outside.png"
    outside.write_bytes(source.read_bytes())
    link = draft / "escape.png"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("Symlink permission unavailable")
    with pytest.raises(ValueError, match="outside"):
        TextureService(settings).inspect(str(link))


def test_prepare_apply_restore_exact_bytes(workspace):
    settings, draft, target, source = workspace
    textures = TextureService(settings)
    original = target.read_bytes()
    plan = textures.prepare(str(source), str(target))
    assert target.read_bytes() == original
    result = textures.apply(plan["id"])
    assert result["status"] == "applied"
    assert target.read_bytes() == source.read_bytes()
    with pytest.raises(ValueError, match="prepared"):
        textures.apply(plan["id"])
    assert textures.restore(plan["id"])["status"] == "restored"
    assert target.read_bytes() == original


@pytest.mark.parametrize("changed", ["source", "target"])
def test_stale_plan_rejected(workspace, changed):
    settings, draft, target, source = workspace
    textures = TextureService(settings)
    plan = textures.prepare(str(source), str(target))
    Image.new("RGB", (256, 512), "green").save(source if changed == "source" else target)
    expected = target.read_bytes()
    with pytest.raises(ValueError, match="changed"):
        textures.apply(plan["id"])
    assert target.read_bytes() == expected


def test_restore_refuses_newer_work(workspace):
    settings, draft, target, source = workspace
    textures = TextureService(settings)
    plan = textures.prepare(str(source), str(target))
    textures.apply(plan["id"])
    Image.new("RGB", (256, 512), "green").save(target)
    newer = target.read_bytes()
    with pytest.raises(ValueError, match="newer work"):
        textures.restore(plan["id"])
    assert target.read_bytes() == newer


def test_disabled_writes_and_target_scope(workspace):
    settings, draft, target, source = workspace
    textures = TextureService(replace(settings, enable_writes=False))
    plan = textures.prepare(str(source), str(target))
    with pytest.raises(ValueError, match="disabled"):
        textures.apply(plan["id"])
    with pytest.raises(ValueError, match="disabled"):
        textures.restore(plan["id"])
    with pytest.raises(ValueError, match="outside"):
        textures.prepare(str(target), str(source))


def test_format_resize_and_invalid_image(workspace):
    settings, draft, target, source = workspace
    textures = TextureService(settings)
    Image.new("RGB", (128, 256)).save(source)
    with pytest.raises(ValueError, match="Dimensions"):
        textures.prepare(str(source), str(target))
    assert textures.prepare(str(source), str(target), True)["allow_resize"]
    Image.new("RGB", (256, 512)).save(source, format="JPEG")
    with pytest.raises(ValueError, match="format"):
        textures.prepare(str(source), str(target))
    source.write_text("not an image")
    with pytest.raises(Exception):
        textures.inspect(str(source))


def test_backup_integrity_and_plan_id(workspace):
    settings, draft, target, source = workspace
    textures = TextureService(settings)
    with pytest.raises(ValueError, match="plan ID"):
        textures.apply("../../escape")
    plan = textures.prepare(str(source), str(target))
    textures.apply(plan["id"])
    (textures._directory(plan["id"]) / "original.bin").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="Backup hash"):
        textures.restore(plan["id"])


def test_preview_is_bounded_and_warns(workspace):
    settings, draft, target, source = workspace
    Image.new("RGB", (1200, 750)).save(source)
    textures = TextureService(settings)
    assert len(textures.inspect(str(source))["warnings"]) == 2
    result = image_info(textures.preview(str(source)))
    assert result["width"] == 1024 and result["height"] == 640


def test_no_implicit_filesystem_scope(tmp_path):
    assert list_projects(Settings(state_dir=tmp_path / "state"))["count"] == 0
    with pytest.raises(ValueError, match="filesystem roots"):
        Settings((Path(tmp_path.anchor),))


def test_recover_after_journal_failure(workspace, monkeypatch):
    settings, draft, target, source = workspace
    textures = TextureService(settings)
    original = target.read_bytes()
    plan = textures.prepare(str(source), str(target))
    save = textures._save

    def fail_final_journal(directory, current):
        if current["status"] == "applied":
            raise OSError("simulated failure after target replacement")
        save(directory, current)

    monkeypatch.setattr(textures, "_save", fail_final_journal)
    with pytest.raises(OSError, match="simulated"):
        textures.apply(plan["id"])
    assert target.read_bytes() == source.read_bytes()
    # A fresh process/service reads the durable backed_up journal and can recover.
    assert TextureService(settings).restore(plan["id"])["status"] == "restored"
    assert target.read_bytes() == original
