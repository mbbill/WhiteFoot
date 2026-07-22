"""Domain-separated identities for ResourceProfile v1 meaning documents."""

from hashlib import sha256
from pathlib import Path

from schema import schema_descriptor


PROPOSAL_SHA256 = "7fc48cc30f94d25be5be1106e3265d92c1b0cdf2bfea5a7a17759a12f3cf092d"
SEMANTICS_DOMAIN = b"WHITEFOOT-RP-C1\0"
WORK_DOMAIN = b"WHITEFOOT-RP-W1\0"
STORAGE_DOMAIN = b"WHITEFOOT-RP-L1\0"


def construct_meaning_digests(
    descriptor_bytes: bytes,
    semantics_bytes: bytes,
    work_bytes: bytes,
    storage_bytes: bytes,
    proposal_digest: bytes,
) -> tuple[bytes, bytes, bytes]:
    """Construct exact identities from their complete immutable inputs."""
    if len(proposal_digest) != 32:
        raise ValueError("proposal digest must contain exactly 32 bytes")
    descriptor = sha256(descriptor_bytes).digest()
    semantics_file = sha256(semantics_bytes).digest()
    work_file = sha256(work_bytes).digest()
    storage_file = sha256(storage_bytes).digest()
    semantics = sha256(
        SEMANTICS_DOMAIN + descriptor + semantics_file + proposal_digest
    ).digest()
    work = sha256(WORK_DOMAIN + work_file + proposal_digest).digest()
    storage = sha256(STORAGE_DOMAIN + storage_file).digest()
    return semantics, work, storage


def meaning_digests(directory: Path) -> tuple[bytes, bytes, bytes]:
    """Return exact semantics, work, and storage model identities."""
    return construct_meaning_digests(
        schema_descriptor(),
        (directory / "SCHEMA-SEMANTICS.md").read_bytes(),
        (directory / "WORK-SCHEDULE.md").read_bytes(),
        (directory / "STORAGE-MODEL.md").read_bytes(),
        bytes.fromhex(PROPOSAL_SHA256),
    )


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    for digest in meaning_digests(root):
        print(digest.hex())
