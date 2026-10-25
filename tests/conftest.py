import pytest
from PIL import Image

from imvu_studio_mcp.config import Settings


@pytest.fixture
def workspace(tmp_path):
    projects = tmp_path / "projects"
    assets = tmp_path / "assets"
    draft = projects / "12345" / "derived999"
    draft.mkdir(parents=True)
    assets.mkdir()
    (draft / "draft_properties.json").write_text('{"ProductName":"Test garment","token":"private"}')
    (draft / "index.xml").write_text(
        '<IMVU><Template><ProductId>999</ProductId><Material Name="cloth" ID="7">'
        '<Texture>diffuse.png</Texture></Material><BodyParts><Mesh ID="41"/></BodyParts>'
        '</Template></IMVU>')
    target, source = draft / "diffuse.png", assets / "replacement.png"
    Image.new("RGB", (256, 512), "red").save(target)
    Image.new("RGB", (256, 512), "blue").save(source)
    settings = Settings((projects,), (assets,), tmp_path / "state", enable_writes=True)
    return settings, draft, target, source
