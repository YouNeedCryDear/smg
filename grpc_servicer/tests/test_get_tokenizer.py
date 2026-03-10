# mypy: ignore-errors
"""Tests for GetTokenizer helpers (tokenizer_bundle module).

These are pure-Python functions with no heavy dependencies,
so no import mocking is needed.
"""

import hashlib
import io
import os
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from smg_grpc_servicer.tokenizer_bundle import (
    TOKENIZER_CHUNK_SIZE,
    TOKENIZER_FILE_EXTENSIONS,
    TOKENIZER_FILE_NAMES,
    collect_tokenizer_files,
    prepare_tokenizer_bundle,
    resolve_tokenizer_source,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _populate_dir(tmp_path: Path, filenames: list[str]) -> None:
    """Create empty files in *tmp_path*."""
    for name in filenames:
        (tmp_path / name).write_bytes(b"")


# ---------------------------------------------------------------------------
# collect_tokenizer_files
# ---------------------------------------------------------------------------


class TestCollectTokenizerFiles:

    def test_picks_up_allowed_filenames(self, tmp_path: Path):
        allowed = ["tokenizer.json", "vocab.txt", "merges.txt", "config.json"]
        _populate_dir(tmp_path, allowed)
        result = collect_tokenizer_files(tmp_path)
        assert {p.name for p in result} == set(allowed)

    def test_picks_up_allowed_extensions(self, tmp_path: Path):
        ext_files = ["sentencepiece.model", "custom.tiktoken", "template.jinja"]
        _populate_dir(tmp_path, ext_files)
        result = collect_tokenizer_files(tmp_path)
        assert {p.name for p in result} == set(ext_files)

    def test_ignores_non_tokenizer_files(self, tmp_path: Path):
        _populate_dir(
            tmp_path,
            [
                "tokenizer.json",
                "model.safetensors",
                "preprocessor_config.json",
                "random.bin",
            ],
        )
        result = collect_tokenizer_files(tmp_path)
        assert [p.name for p in result] == ["tokenizer.json"]

    def test_ignores_subdirectories(self, tmp_path: Path):
        (tmp_path / "tokenizer.json").write_bytes(b"{}")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "vocab.txt").write_bytes(b"")
        result = collect_tokenizer_files(tmp_path)
        assert [p.name for p in result] == ["tokenizer.json"]

    def test_ignores_symlink_escapes(self, tmp_path: Path):
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "vocab.txt").write_bytes(b"secret")

        source = tmp_path / "source"
        source.mkdir()
        (source / "tokenizer.json").write_bytes(b"{}")
        os.symlink(outside / "vocab.txt", source / "vocab.txt")

        result = collect_tokenizer_files(source)
        names = [p.name for p in result]
        assert "tokenizer.json" in names
        assert "vocab.txt" not in names

    def test_returns_sorted_by_name(self, tmp_path: Path):
        _populate_dir(tmp_path, ["vocab.txt", "added_tokens.json", "merges.txt"])
        result = collect_tokenizer_files(tmp_path)
        names = [p.name for p in result]
        assert names == sorted(names, key=str.lower)

    def test_empty_directory(self, tmp_path: Path):
        assert collect_tokenizer_files(tmp_path) == []

    def test_all_allowed_filenames(self, tmp_path: Path):
        _populate_dir(tmp_path, list(TOKENIZER_FILE_NAMES))
        result = collect_tokenizer_files(tmp_path)
        assert {p.name for p in result} == TOKENIZER_FILE_NAMES

    def test_all_allowed_extensions(self, tmp_path: Path):
        ext_files = [f"test{ext}" for ext in TOKENIZER_FILE_EXTENSIONS]
        _populate_dir(tmp_path, ext_files)
        result = collect_tokenizer_files(tmp_path)
        assert {p.name for p in result} == set(ext_files)


# ---------------------------------------------------------------------------
# resolve_tokenizer_source
# ---------------------------------------------------------------------------


class TestResolveTokenizerSource:

    def test_local_directory(self, tmp_path: Path):
        (tmp_path / "tokenizer.json").write_bytes(b"{}")
        result = resolve_tokenizer_source(model_path=str(tmp_path))
        assert result == tmp_path.resolve()

    def test_local_file_returns_parent(self, tmp_path: Path):
        tok_file = tmp_path / "tokenizer.json"
        tok_file.write_bytes(b"{}")
        result = resolve_tokenizer_source(model_path=str(tok_file))
        assert result == tmp_path.resolve()

    def test_tokenizer_field_takes_priority(self, tmp_path: Path):
        model_dir = tmp_path / "model"
        model_dir.mkdir()
        tok_dir = tmp_path / "tokenizer"
        tok_dir.mkdir()
        (tok_dir / "tokenizer.json").write_bytes(b"{}")

        result = resolve_tokenizer_source(
            model_path=str(model_dir), tokenizer_path=str(tok_dir)
        )
        assert result == tok_dir.resolve()

    def test_falls_back_to_huggingface_cache(self, tmp_path: Path):
        cached_dir = tmp_path / "cached"
        cached_dir.mkdir()
        # The function does `from huggingface_hub import snapshot_download`
        # so we need to mock the module in sys.modules.
        import types

        fake_hub = types.ModuleType("huggingface_hub")
        fake_hub.snapshot_download = lambda raw, **kw: str(cached_dir)
        with patch.dict("sys.modules", {"huggingface_hub": fake_hub}):
            result = resolve_tokenizer_source(model_path="org/model-name")
            assert result == cached_dir

    def test_raises_when_nothing_works(self, tmp_path: Path):
        with patch.dict("sys.modules", {"huggingface_hub": None}):
            with pytest.raises(FileNotFoundError, match="does not exist"):
                resolve_tokenizer_source(model_path="nonexistent/model")

    def test_raises_when_no_model_or_tokenizer(self):
        with pytest.raises(FileNotFoundError, match="Neither tokenizer nor model"):
            resolve_tokenizer_source(model_path="")


# ---------------------------------------------------------------------------
# prepare_tokenizer_bundle
# ---------------------------------------------------------------------------


class TestPrepareTokenizerBundle:

    def test_produces_valid_zip(self, tmp_path: Path):
        files = ["tokenizer.json", "vocab.txt", "merges.txt"]
        for f in files:
            (tmp_path / f).write_text(f"content-{f}")

        bundle_bytes, fingerprint = prepare_tokenizer_bundle(model_path=str(tmp_path))

        with zipfile.ZipFile(io.BytesIO(bundle_bytes)) as zf:
            assert set(zf.namelist()) == set(files)
            for f in files:
                assert zf.read(f) == f"content-{f}".encode()

    def test_sha256_is_correct(self, tmp_path: Path):
        (tmp_path / "tokenizer.json").write_text("{}")
        bundle_bytes, fingerprint = prepare_tokenizer_bundle(model_path=str(tmp_path))
        assert fingerprint == hashlib.sha256(bundle_bytes).hexdigest()

    def test_raises_when_no_artifacts(self, tmp_path: Path):
        (tmp_path / "model.safetensors").write_bytes(b"\x00")
        with pytest.raises(FileNotFoundError, match="No tokenizer artifacts"):
            prepare_tokenizer_bundle(model_path=str(tmp_path))

    def test_deterministic_output(self, tmp_path: Path):
        (tmp_path / "tokenizer.json").write_text("{}")
        (tmp_path / "vocab.txt").write_text("hello")
        b1, h1 = prepare_tokenizer_bundle(model_path=str(tmp_path))
        b2, h2 = prepare_tokenizer_bundle(model_path=str(tmp_path))
        assert b1 == b2
        assert h1 == h2

    def test_large_bundle_exceeds_chunk_size(self, tmp_path: Path):
        # Use random-ish bytes so compression can't shrink below chunk size
        import random

        rng = random.Random(42)
        large_content = bytes(rng.getrandbits(8) for _ in range(TOKENIZER_CHUNK_SIZE + 1000))
        (tmp_path / "sentencepiece.model").write_bytes(large_content)
        bundle_bytes, _ = prepare_tokenizer_bundle(model_path=str(tmp_path))
        assert len(bundle_bytes) > TOKENIZER_CHUNK_SIZE
