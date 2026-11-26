"""Program images kept in the database (default) or on disk, and served safely."""

import io
import os
from datetime import datetime, timedelta, timezone

import pytest
from PIL import Image
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from app.core.config import Settings, settings
from app.db.models import Program, UploadedImage
from app.services import upload_service
from app.services.upload_service import NAME_PATTERN, UNUSED_KEEP_FOR, delete_unused_images


def png(size=(40, 30), color="red") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture
def admin(make_user, auth):
    return auth(make_user(role="admin"))


def upload(client, headers, data=None, name="banner.png"):
    r = client.post("/api/admin/uploads/image", files={"file": (name, data or png(), "image/png")}, headers=headers)
    assert r.status_code == 201, r.text
    url = r.json()["data"]["url"]
    return url, "/uploads/" + url.rsplit("/", 1)[1]


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _program(db, slug="p1", image="", **over):
    p = Program(slug=slug, title="P", category="c", tagline="t", image=image, price=150, **over)
    db.add(p)
    db.commit()
    return p


# --------------------------------------------------------------------------
# Database storage (the default)
# --------------------------------------------------------------------------


class TestDatabaseStorage:
    def test_database_is_the_default(self):
        assert Settings(_env_file=None).upload_storage == "database"

    def test_an_upload_becomes_a_row_and_no_file(self, client, db, admin, monkeypatch, tmp_path):
        monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "nothing-here"))
        _, path = upload(client, admin)
        db.expire_all()
        rows = db.query(UploadedImage).all()
        assert len(rows) == 1 and path.endswith(rows[0].name)
        assert rows[0].content_type == "image/png" and rows[0].size == len(rows[0].data) > 0
        assert not (tmp_path / "nothing-here").exists() or not any((tmp_path / "nothing-here").iterdir())

    def test_the_served_bytes_are_the_cleaned_image(self, client, db, admin):
        _, path = upload(client, admin, png((3000, 2000)))
        served = client.get(path)
        assert served.status_code == 200 and served.headers["content-type"] == "image/png"
        assert max(Image.open(io.BytesIO(served.content)).size) <= 1600  # the downscaled copy, not the original
        db.expire_all()
        assert served.content == db.query(UploadedImage).one().data

    def test_images_are_cached_for_a_year_and_cannot_be_sniffed(self, client, admin):
        _, path = upload(client, admin)
        h = client.get(path).headers
        assert "max-age=31536000" in h["cache-control"] and "immutable" in h["cache-control"]
        assert h["x-content-type-options"] == "nosniff"

    def test_head_requests_work(self, client, admin):
        _, path = upload(client, admin)
        r = client.head(path)
        assert r.status_code == 200 and r.headers["content-type"] == "image/png"

    @pytest.mark.parametrize("fmt,ctype,ext", [("PNG", "image/png", ".png"), ("JPEG", "image/jpeg", ".jpg"), ("WEBP", "image/webp", ".webp")])
    def test_each_format_is_served_with_its_own_content_type(self, client, admin, fmt, ctype, ext):
        buf = io.BytesIO()
        Image.new("RGB", (20, 20), "blue").save(buf, fmt)
        _, path = upload(client, admin, buf.getvalue(), "x" + ext)
        r = client.get(path)
        assert r.headers["content-type"] == ctype and path.endswith(ext)

    def test_the_image_is_public_no_login_needed(self, client, admin):
        _, path = upload(client, admin)
        client.cookies.clear()
        assert client.get(path).status_code == 200

    def test_an_unknown_name_is_404(self, client):
        assert client.get("/uploads/" + "a" * 32 + ".png").status_code == 404

    @pytest.mark.parametrize(
        "name",
        [
            "../../etc/passwd",
            "..%2f..%2fetc%2fpasswd",
            "%2e%2e/secret.png",
            "a" * 32,  # no extension
            "a" * 32 + ".svg",
            "a" * 32 + ".png.php",
            "A" * 32 + ".png",  # uppercase is never generated
            "a" * 31 + ".png",
            "a" * 33 + ".png",
            "conftest.py",
            ".env",
        ],
    )
    def test_only_generated_names_are_served(self, client, name):
        assert client.get("/uploads/" + name).status_code == 404

    @pytest.mark.parametrize("name", ["secret-notes.txt", "A" * 32 + ".png", "a" * 32 + ".gif", "readme"])
    def test_a_real_file_with_a_disallowed_name_is_still_never_served(self, client, name):
        """Even if such a file somehow exists in the upload folder, only generated names are served."""
        (upload_service.upload_root() / name).write_bytes(png())
        assert client.get("/uploads/" + name).status_code == 404

    def test_name_pattern_matches_exactly_what_uploads_generate(self, client, admin):
        _, path = upload(client, admin)
        assert NAME_PATTERN.fullmatch(path.rsplit("/", 1)[1])

    def test_the_stored_image_can_be_used_on_a_program(self, client, admin):
        url, path = upload(client, admin)
        body = {"slug": "with-image", "title": "T", "category": "C", "image": url}
        assert client.post("/api/admin/programs", json=body, headers=admin).status_code == 201
        assert client.get(path).status_code == 200


class TestMysqlCompatibility:
    def test_mysql_gets_a_column_big_enough_for_images(self):
        """A plain MySQL BLOB holds 64 KB, which most images exceed."""
        ddl = str(CreateTable(UploadedImage.__table__).compile(dialect=mysql.dialect()))
        assert "LONGBLOB" in ddl

    def test_other_databases_use_their_normal_binary_type(self):
        from sqlalchemy.dialects import postgresql, sqlite

        assert "BYTEA" in str(CreateTable(UploadedImage.__table__).compile(dialect=postgresql.dialect()))
        assert "BLOB" in str(CreateTable(UploadedImage.__table__).compile(dialect=sqlite.dialect()))

    def test_a_large_image_round_trips_through_the_database(self, client, db, admin):
        import random

        rng = random.Random(1)
        noisy = Image.frombytes("RGB", (900, 900), bytes(rng.getrandbits(8) for _ in range(900 * 900 * 3)))
        buf = io.BytesIO()
        noisy.save(buf, "PNG")
        assert len(buf.getvalue()) > 1_000_000  # far beyond MySQL's 64 KB BLOB limit
        _, path = upload(client, admin, buf.getvalue())
        assert len(client.get(path).content) > 1_000_000


# --------------------------------------------------------------------------
# Disk storage and images that were stored before the database option existed
# --------------------------------------------------------------------------


class TestDiskStorage:
    def test_disk_mode_writes_a_file_and_no_row(self, client, db, admin, monkeypatch):
        monkeypatch.setattr(settings, "upload_storage", "disk")
        _, path = upload(client, admin)
        name = path.rsplit("/", 1)[1]
        assert (upload_service.upload_root() / name).is_file()
        db.expire_all()
        assert db.query(UploadedImage).count() == 0
        assert client.get(path).status_code == 200

    def test_images_already_on_disk_keep_working_in_database_mode(self, client):
        name = "b" * 32 + ".png"
        (upload_service.upload_root() / name).write_bytes(png())
        assert settings.upload_storage == "database"
        r = client.get("/uploads/" + name)
        assert r.status_code == 200 and r.headers["content-type"] == "image/png"

    def test_the_database_copy_wins_over_a_disk_file_with_the_same_name(self, client, db):
        name = "c" * 32 + ".png"
        (upload_service.upload_root() / name).write_bytes(png(color="red"))
        db.add(UploadedImage(name=name, content_type="image/png", data=png(color="green"), size=1))
        db.commit()
        got = Image.open(io.BytesIO(client.get("/uploads/" + name).content)).convert("RGB").getpixel((0, 0))
        assert got[1] > got[0]  # green, from the database

    def test_an_invalid_storage_value_is_rejected_at_start_up(self):
        with pytest.raises(Exception):
            Settings(upload_storage="floppy-disk", _env_file=None)


# --------------------------------------------------------------------------
# Clean-up of images nothing uses
# --------------------------------------------------------------------------


class TestCleanup:
    def _row(self, db, name, age_days):
        db.add(UploadedImage(name=name, content_type="image/png", data=b"x", size=1, created_at=_now() - timedelta(days=age_days)))
        db.commit()

    def test_old_unused_images_are_deleted(self, db):
        self._row(db, "1" * 32 + ".png", UNUSED_KEEP_FOR.days + 1)
        assert delete_unused_images(db) == 1
        assert db.query(UploadedImage).count() == 0

    def test_recent_images_are_kept_even_if_unused(self, db):
        """An admin may have the editor open with an image uploaded but not saved yet."""
        self._row(db, "2" * 32 + ".png", 1)
        assert delete_unused_images(db) == 0

    def test_images_a_program_uses_are_never_deleted(self, db):
        name = "3" * 32 + ".png"
        self._row(db, name, 400)
        _program(db, image=f"https://api.example.com/uploads/{name}")
        assert delete_unused_images(db) == 0
        assert db.get(UploadedImage, name) is not None

    def test_inactive_programs_still_protect_their_image(self, db):
        name = "4" * 32 + ".png"
        self._row(db, name, 400)
        _program(db, image=f"/uploads/{name}", is_active=False)
        assert delete_unused_images(db) == 0

    def test_only_the_unused_ones_go(self, db):
        used, unused = "5" * 32 + ".png", "6" * 32 + ".png"
        self._row(db, used, 30)
        self._row(db, unused, 30)
        _program(db, image=f"https://x.test/uploads/{used}")
        assert delete_unused_images(db) == 1
        assert db.get(UploadedImage, used) is not None and db.get(UploadedImage, unused) is None

    def test_uploading_triggers_the_clean_up(self, client, db, admin):
        stale = "7" * 32 + ".png"
        self._row(db, stale, 30)
        upload(client, admin)
        db.expire_all()
        assert db.get(UploadedImage, stale) is None
        assert db.query(UploadedImage).count() == 1  # just the new one

    def test_replacing_a_programs_image_eventually_frees_the_old_one(self, client, db, admin):
        old_url, old_path = upload(client, admin, png(color="red"))
        client.post("/api/admin/programs", json={"slug": "swap", "title": "T", "category": "C", "image": old_url}, headers=admin)
        new_url, _ = upload(client, admin, png(color="green"))
        client.put("/api/admin/programs/swap", json={"image": new_url}, headers=admin)
        old_name = old_path.rsplit("/", 1)[1]
        db.query(UploadedImage).filter(UploadedImage.name == old_name).update({"created_at": _now() - timedelta(days=30)})
        db.commit()
        upload(client, admin, png(color="blue"))  # the next upload sweeps
        db.expire_all()
        assert db.get(UploadedImage, old_name) is None
        assert client.get("/uploads/" + new_url.rsplit("/", 1)[1]).status_code == 200  # the one in use survives
