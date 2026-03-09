"""Tokenizer bundle utilities.

Pure-Python helpers for collecting tokenizer artifacts, resolving their
source directory, and packaging them into a deterministic zip bundle.
No heavy dependencies (torch, vLLM, gRPC, etc.).

Aligned with crates/tokenizer/src/hub.rs::is_tokenizer_file.
"""

import hashlib
import io
import zipfile
from pathlib import Path

TOKENIZER_CHUNK_SIZE = 2 * 1024 * 1024  # 2MB

# Specific filenames for .json/.txt (to avoid bundling unrelated files like
# model.safetensors.index.json or preprocessor_config.json).
TOKENIZER_FILE_NAMES = {
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "added_tokens.json",
    "vocab.json",
    "vocab.txt",
    "merges.txt",
    "chat_template.json",
    "config.json",
}

# Extension-based matching for file types that are always tokenizer artifacts.
TOKENIZER_FILE_EXTENSIONS = {".model", ".tiktoken", ".jinja"}


def collect_tokenizer_files(source_root: Path) -> list[Path]:
    """Collect tokenizer-related files only (exclude model weights).

    Uses a strict allowlist aligned with crates/tokenizer/src/hub.rs
    to avoid bundling unrelated files.
    """
    selected: list[Path] = []
    root_resolved = source_root.resolve()

    for path in source_root.iterdir():
        if not path.is_file():
            continue
        try:
            resolved = path.resolve()
        except OSError:
            continue

        # Skip symlink escapes
        if not resolved.is_relative_to(root_resolved):
            continue

        name = path.name.lower()
        suffix = path.suffix.lower()
        if name in TOKENIZER_FILE_NAMES or suffix in TOKENIZER_FILE_EXTENSIONS:
            selected.append(path)

    selected.sort(key=lambda p: p.name.lower())
    return selected


def resolve_tokenizer_source(
    model_path: str,
    tokenizer_path: str | None = None,
) -> Path:
    """Resolve tokenizer artifact root.

    Handles both local paths and HuggingFace model IDs by checking the
    download cache directory used by vLLM/transformers.
    """
    raw = (tokenizer_path or "").strip() or model_path
    if not raw:
        raise FileNotFoundError(
            "Neither tokenizer nor model path is configured"
        )

    p = Path(raw).expanduser().resolve()
    if p.is_dir():
        return p
    if p.is_file():
        return p.parent

    # Not a local path — try HuggingFace cache via transformers/huggingface_hub
    try:
        from huggingface_hub import snapshot_download

        cached_dir = snapshot_download(raw, local_files_only=True)
        return Path(cached_dir)
    except Exception:
        raise FileNotFoundError(
            f"Tokenizer source path does not exist and is not a cached HuggingFace model: {raw}"
        )


def prepare_tokenizer_bundle(
    model_path: str,
    tokenizer_path: str | None = None,
) -> tuple[bytes, str]:
    """Build a deterministic zip bundle of tokenizer artifacts and return (bytes, sha256)."""
    source_root = resolve_tokenizer_source(model_path, tokenizer_path)
    files = collect_tokenizer_files(source_root)

    if not files:
        raise FileNotFoundError(
            f"No tokenizer artifacts found under '{source_root}'"
        )

    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6,
    ) as archive:
        for path in files:
            archive.write(path, path.name)

    bundle_bytes = buffer.getvalue()
    fingerprint = hashlib.sha256(bundle_bytes).hexdigest()
    return bundle_bytes, fingerprint
