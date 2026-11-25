"""Admin portal: create programs, edit every field, upload images."""

import io
import os

import pytest
from PIL import Image

from app.core.config import settings
from app.db.models import Program

FULL_PROGRAM = {
    "slug": "blockchain-basics",
    "title": "Blockchain Basics",
    "category": "Emerging Tech",  # a brand-new category
    "tagline": "Learn how blockchains actually work.",
    "image": "https://example.com/banner.jpg",
    "duration": "6 Weeks",
    "price": 299,
    "mode": "Hybrid",
    "certificate": False,
    "liveProjects": 4,
    "skills": ["Solidity", "  Ethereum  ", "", "Web3.js"],
    "tools": ["Hardhat", "Remix"],
    "outcomes": ["Deploy a smart contract", "Explain consensus"],
    "eligibility": "Basic programming knowledge.",
    "curriculum": [
        {"week": "Week 1", "title": "Foundations", "points": ["Hashing", "Blocks", " "]},
        {"week": "Week 2", "title": "Smart contracts", "points": ["Solidity basics"]},
    ],
    "is_active": True,
}


def _image_bytes(fmt="PNG", size=(40, 30), mode="RGB") -> bytes:
    buf = io.BytesIO()
    Image.new(mode, size, "red").save(buf, fmt)
    return buf.getvalue()


@pytest.fixture
def admin_headers(make_user, auth):
    return auth(make_user(role="admin"))


def _upload(client, headers, data: bytes, filename="banner.png", content_type="image/png"):
    return client.post("/api/admin/uploads/image", files={"file": (filename, data, content_type)}, headers=headers)


# --------------------------------------------------------------------------
# Create a program with everything
# --------------------------------------------------------------------------


class TestCreateProgram:
    def test_creates_with_all_fields_and_public_api_returns_them(self, client, admin_headers):
        r = client.post("/api/admin/programs", json=FULL_PROGRAM, headers=admin_headers)
        assert r.status_code == 201, r.text
        public = client.get("/api/programs/blockchain-basics").json()["data"]
        assert public["title"] == "Blockchain Basics"
        assert public["category"] == "Emerging Tech"
        assert public["tagline"] == FULL_PROGRAM["tagline"]
        assert public["image"] == FULL_PROGRAM["image"]
        assert public["duration"] == "6 Weeks"
        assert public["price"] == 299
        assert public["mode"] == "Hybrid"
        assert public["certificate"] is False
        assert public["liveProjects"] == 4
        assert public["tools"] == ["Hardhat", "Remix"]
        assert public["outcomes"] == ["Deploy a smart contract", "Explain consensus"]
        assert public["eligibility"] == "Basic programming knowledge."
        assert [w["title"] for w in public["curriculum"]] == ["Foundations", "Smart contracts"]

    def test_blank_and_padded_list_entries_are_cleaned(self, client, admin_headers):
        client.post("/api/admin/programs", json=FULL_PROGRAM, headers=admin_headers)
        public = client.get("/api/programs/blockchain-basics").json()["data"]
        assert public["skills"] == ["Solidity", "Ethereum", "Web3.js"]
        assert public["curriculum"][0]["points"] == ["Hashing", "Blocks"]

    def test_new_category_appears_in_the_public_filter(self, client, admin_headers):
        client.post("/api/admin/programs", json=FULL_PROGRAM, headers=admin_headers)
        assert "Emerging Tech" in client.get("/api/programs/categories").json()["data"]

    def test_new_program_is_listed_publicly(self, client, admin_headers):
        client.post("/api/admin/programs", json=FULL_PROGRAM, headers=admin_headers)
        slugs = [p["slug"] for p in client.get("/api/programs?limit=100").json()["data"]]
        assert "blockchain-basics" in slugs

    def test_duplicate_slug_is_rejected(self, client, admin_headers):
        assert client.post("/api/admin/programs", json=FULL_PROGRAM, headers=admin_headers).status_code == 201
        assert client.post("/api/admin/programs", json=FULL_PROGRAM, headers=admin_headers).status_code == 409

    @pytest.mark.parametrize("slug", ["Has Caps", "has space", "under_score", "-lead", "trail-", "dou--ble", "../etc", ""])
    def test_unsafe_slugs_are_rejected(self, client, admin_headers, slug):
        r = client.post("/api/admin/programs", json={**FULL_PROGRAM, "slug": slug}, headers=admin_headers)
        assert r.status_code == 422

    @pytest.mark.parametrize("image", ["javascript:alert(1)", "data:text/html,hi", "ftp://x/y.png", "/etc/passwd"])
    def test_non_http_image_urls_are_rejected(self, client, admin_headers, image):
        r = client.post("/api/admin/programs", json={**FULL_PROGRAM, "image": image}, headers=admin_headers)
        assert r.status_code == 422

    def test_blank_image_is_allowed(self, client, admin_headers):
        r = client.post("/api/admin/programs", json={**FULL_PROGRAM, "image": ""}, headers=admin_headers)
        assert r.status_code == 201

    @pytest.mark.parametrize(
        "field,value",
        [("liveProjects", -1), ("liveProjects", 99), ("title", ""), ("category", ""), ("duration", ""), ("mode", "")],
    )
    def test_invalid_values_are_rejected(self, client, admin_headers, field, value):
        assert client.post("/api/admin/programs", json={**FULL_PROGRAM, field: value}, headers=admin_headers).status_code == 422

    def test_students_cannot_create(self, client, make_user, auth):
        assert client.post("/api/admin/programs", json=FULL_PROGRAM, headers=auth(make_user())).status_code == 403

    def test_anonymous_cannot_create(self, client):
        assert client.post("/api/admin/programs", json=FULL_PROGRAM).status_code == 401


# --------------------------------------------------------------------------
# Edit every field
# --------------------------------------------------------------------------


class TestEditProgram:
    @pytest.fixture(autouse=True)
    def _program(self, client, admin_headers):
        client.post("/api/admin/programs", json=FULL_PROGRAM, headers=admin_headers)

    def _put(self, client, headers, body):
        return client.put("/api/admin/programs/blockchain-basics", json=body, headers=headers)

    def test_every_editable_field_can_be_changed(self, client, admin_headers):
        changes = {
            "title": "Blockchain Deep Dive",
            "category": "Data & AI",
            "tagline": "New tagline",
            "image": "https://example.com/new.png",
            "duration": "8 Weeks",
            "price": 499,
            "mode": "Remote",
            "certificate": True,
            "liveProjects": 2,
            "skills": ["Rust"],
            "tools": ["Foundry"],
            "outcomes": ["Audit a contract"],
            "eligibility": "None.",
            "curriculum": [{"week": "Week 1", "title": "Only week", "points": ["One"]}],
            "is_active": False,
        }
        r = self._put(client, admin_headers, changes)
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["title"] == "Blockchain Deep Dive"
        assert data["category"] == "Data & AI"
        assert data["tagline"] == "New tagline"
        assert data["image"] == "https://example.com/new.png"
        assert data["duration"] == "8 Weeks"
        assert data["price"] == 499
        assert data["mode"] == "Remote"
        assert data["certificate"] is True
        assert data["liveProjects"] == 2
        assert data["skills"] == ["Rust"]
        assert data["tools"] == ["Foundry"]
        assert data["outcomes"] == ["Audit a contract"]
        assert data["eligibility"] == "None."
        assert data["curriculum"] == [{"week": "Week 1", "title": "Only week", "points": ["One"]}]
        assert data["isActive"] is False

    def test_partial_update_leaves_other_fields_alone(self, client, admin_headers):
        self._put(client, admin_headers, {"tagline": "Only this changes"})
        data = client.get("/api/admin/programs", headers=admin_headers).json()["data"]
        mine = next(p for p in data if p["slug"] == "blockchain-basics")
        assert mine["tagline"] == "Only this changes"
        assert mine["title"] == "Blockchain Basics" and mine["price"] == 299 and mine["skills"][0] == "Solidity"

    def test_lists_can_be_emptied(self, client, admin_headers):
        data = self._put(client, admin_headers, {"skills": [], "curriculum": []}).json()["data"]
        assert data["skills"] == [] and data["curriculum"] == []

    def test_slug_cannot_be_changed(self, client, db, admin_headers):
        r = self._put(client, admin_headers, {"slug": "renamed", "title": "Still here"})
        assert r.status_code == 200
        db.expire_all()
        assert db.get(Program, "blockchain-basics").title == "Still here"
        assert db.get(Program, "renamed") is None

    def test_deactivate_hides_it_and_reactivate_restores_it(self, client, admin_headers):
        self._put(client, admin_headers, {"is_active": False})
        assert client.get("/api/programs/blockchain-basics").status_code == 404
        self._put(client, admin_headers, {"is_active": True})
        assert client.get("/api/programs/blockchain-basics").status_code == 200

    def test_admin_list_includes_inactive_programs(self, client, admin_headers):
        self._put(client, admin_headers, {"is_active": False})
        slugs = [p["slug"] for p in client.get("/api/admin/programs", headers=admin_headers).json()["data"]]
        assert "blockchain-basics" in slugs

    def test_unknown_program_is_404(self, client, admin_headers):
        assert client.put("/api/admin/programs/nope", json={"title": "x"}, headers=admin_headers).status_code == 404

    def test_students_cannot_edit(self, client, make_user, auth):
        r = client.put("/api/admin/programs/blockchain-basics", json={"title": "hacked"}, headers=auth(make_user()))
        assert r.status_code == 403


# --------------------------------------------------------------------------
# Image upload
# --------------------------------------------------------------------------


class TestImageUpload:
    @pytest.mark.parametrize("fmt,ext", [("PNG", ".png"), ("JPEG", ".jpg"), ("WEBP", ".webp")])
    def test_valid_images_are_stored_and_served(self, client, admin_headers, fmt, ext):
        r = _upload(client, admin_headers, _image_bytes(fmt))
        assert r.status_code == 201, r.text
        url = r.json()["data"]["url"]
        assert url.endswith(ext) and "/uploads/" in url
        served = client.get("/uploads/" + url.rsplit("/", 1)[1])
        assert served.status_code == 200
        assert Image.open(io.BytesIO(served.content)).format == fmt

    def test_returned_url_can_be_saved_on_a_program(self, client, admin_headers):
        url = _upload(client, admin_headers, _image_bytes()).json()["data"]["url"]
        body = {**FULL_PROGRAM, "image": url}
        assert client.post("/api/admin/programs", json=body, headers=admin_headers).status_code == 201

    def test_url_uses_the_public_api_url_when_configured(self, client, admin_headers, monkeypatch):
        monkeypatch.setattr(settings, "api_public_url", "https://api.example.com/")
        url = _upload(client, admin_headers, _image_bytes()).json()["data"]["url"]
        assert url.startswith("https://api.example.com/uploads/")

    def test_client_filename_is_never_used(self, client, admin_headers):
        url = _upload(client, admin_headers, _image_bytes(), filename="../../evil name.php").json()["data"]["url"]
        name = url.rsplit("/", 1)[1]
        assert "evil" not in name and ".php" not in name and ".." not in name
        assert len(name.split(".")[0]) == 32

    def test_files_land_only_in_the_upload_dir(self, client, admin_headers):
        _upload(client, admin_headers, _image_bytes(), filename="../../escape.png")
        assert not os.path.exists(os.path.join(os.path.dirname(settings.upload_dir), "escape.png"))

    def test_large_images_are_downscaled(self, client, admin_headers):
        url = _upload(client, admin_headers, _image_bytes(size=(3000, 2000))).json()["data"]["url"]
        stored = client.get("/uploads/" + url.rsplit("/", 1)[1]).content
        assert max(Image.open(io.BytesIO(stored)).size) <= 1600

    def test_exif_metadata_is_stripped(self, client, admin_headers):
        img = Image.new("RGB", (50, 50), "blue")
        exif = img.getexif()
        exif[0x010E] = "secret camera description"
        buf = io.BytesIO()
        img.save(buf, "JPEG", exif=exif)
        assert b"secret camera description" in buf.getvalue()
        url = _upload(client, admin_headers, buf.getvalue(), "p.jpg", "image/jpeg").json()["data"]["url"]
        stored = client.get("/uploads/" + url.rsplit("/", 1)[1]).content
        assert b"secret camera description" not in stored

    def test_content_is_checked_not_the_declared_type(self, client, admin_headers):
        html = b"<html><script>alert(1)</script></html>"
        r = _upload(client, admin_headers, html, "innocent.png", "image/png")
        assert r.status_code == 400

    def test_svg_is_rejected(self, client, admin_headers):
        svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
        assert _upload(client, admin_headers, svg, "x.svg", "image/svg+xml").status_code == 400

    def test_gif_is_rejected(self, client, admin_headers):
        assert _upload(client, admin_headers, _image_bytes("GIF"), "x.gif", "image/gif").status_code == 400

    def test_corrupt_image_is_rejected(self, client, admin_headers):
        assert _upload(client, admin_headers, _image_bytes()[:30]).status_code == 400

    def test_empty_file_is_rejected(self, client, admin_headers):
        assert _upload(client, admin_headers, b"").status_code == 400

    def test_oversized_file_is_rejected(self, client, admin_headers, monkeypatch):
        monkeypatch.setattr(settings, "max_upload_mb", 0)  # anything non-empty is now "too big"
        assert _upload(client, admin_headers, _image_bytes()).status_code == 413

    def test_missing_file_field_is_a_validation_error(self, client, admin_headers):
        assert client.post("/api/admin/uploads/image", headers=admin_headers).status_code == 422

    def test_students_cannot_upload(self, client, make_user, auth):
        assert _upload(client, auth(make_user()), _image_bytes()).status_code == 403

    def test_anonymous_cannot_upload(self, client):
        r = client.post("/api/admin/uploads/image", files={"file": ("a.png", _image_bytes(), "image/png")})
        assert r.status_code == 401
