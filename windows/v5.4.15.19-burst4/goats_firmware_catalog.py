"""Verify the signed release entry used by the firmware download and flash paths."""

import base64
import binascii
import json
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


# Set a pinned Ed25519 public key here after agreeing on release key custody.
# Tests inject an ephemeral key. The distributed Manager uses built-in releases.
PUBLIC_KEY = None
MAX_CATALOG_BYTES = 8192
VERSION = re.compile(r"RC[1-9][0-9]{0,5}(?:\.[1-9][0-9]{0,5})?")


def version_number(version):
    if not isinstance(version, str) or VERSION.fullmatch(version) is None:
        raise ValueError("Versione nel catalogo firmware non valida.")
    return tuple(map(int, version[2:].split(".")))


def verify_catalog(envelope, model, slot_limit, minimum_version):
    if PUBLIC_KEY is None:
        raise ValueError("Catalogo firmware firmato non configurato.")
    if len(envelope) > MAX_CATALOG_BYTES:
        raise ValueError("Catalogo firmware oltre il limite di dimensione.")
    try:
        signed = json.loads(envelope)
        payload = base64.b64decode(signed["payload"], validate=True)
        signature = base64.b64decode(signed["signature"], validate=True)
        Ed25519PublicKey.from_public_bytes(PUBLIC_KEY).verify(signature, payload)
        entry = json.loads(payload)
    except (TypeError, KeyError, ValueError, binascii.Error, InvalidSignature) as exc:
        raise ValueError("Firma del catalogo firmware non valida.") from exc

    if not isinstance(entry, dict) or entry.get("schema") != 1 or entry.get("model") != model:
        raise ValueError("Catalogo firmware incompatibile con il modello.")
    if version_number(entry.get("version")) < version_number(minimum_version):
        raise ValueError("Versione del catalogo precedente alla versione integrata nel Manager.")
    if type(entry.get("size")) is not int or not 112 <= entry["size"] <= slot_limit:
        raise ValueError("Dimensione firmware nel catalogo fuori dai limiti dello slot.")
    digest = entry.get("sha256")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ValueError("SHA-256 nel catalogo firmware non valido.")
    return entry
