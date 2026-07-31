from __future__ import annotations

import html
import ipaddress
import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import urlsplit


_REDACTED = " [REDACTED] "


@dataclass(frozen=True)
class DetectionResult:
    hard_block_categories: tuple[str, ...]
    confirm_categories: tuple[str, ...]
    redacted_text: str


class SensitiveDataDetector:
    _HARD_PATTERNS = (
        ("private_key", re.compile(r"-----BEGIN(?: [A-Z0-9]+)? PRIVATE KEY-----", re.IGNORECASE)),
        ("authorization_token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE)),
        ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
        ("api_key", re.compile(r"\b(?:AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9_-]{20,})\b")),
        ("credential_assignment", re.compile(r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*[^\s]{6,}")),
        ("credential_url", re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s/:]+:[^\s/@]+@", re.IGNORECASE)),
        ("dotenv_secret", re.compile(r"(?im)^\s*[A-Z0-9_]*(?:SECRET|TOKEN|PASSWORD|API_KEY)[A-Z0-9_]*\s*=\s*\S{6,}\s*$")),
    )
    _CONFIRM_PATTERNS = (
        ("email", re.compile(r"(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])", re.IGNORECASE)),
        ("phone", re.compile(r"(?<!\d)(?:\+?81[- ]?|0)\d{1,4}[- ]?\d{1,4}[- ]?\d{3,4}(?!\d)")),
        ("local_path", re.compile(r"(?:/(?:Users|home|private|var|etc|opt)/[^\s]+|[A-Za-z]:\\(?:[^\s\\]+\\)+[^\s]+)")),
        ("ip_address", re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")),
        ("internal_host", re.compile(r"\b[a-z0-9][a-z0-9.-]*\.(?:local|internal|intranet|lan)\b", re.IGNORECASE)),
        ("confidential_marker", re.compile(r"(?:社外秘|部外秘|機密情報|顧客情報|個人情報|internal[- ]only|confidential|do not share)", re.IGNORECASE)),
        ("code_or_log", re.compile(r"```|Traceback \(most recent call last\)|\b(?:ERROR|FATAL)\b.*\b(?:at|line|exception)\b", re.IGNORECASE)),
    )

    def inspect(self, text: str) -> DetectionResult:
        hard: list[str] = []
        confirm: list[str] = []
        redacted = text
        for category, pattern in self._HARD_PATTERNS:
            if pattern.search(redacted):
                hard.append(category)
                redacted = pattern.sub(_REDACTED, redacted)
        for category, pattern in self._CONFIRM_PATTERNS:
            if pattern.search(redacted):
                confirm.append(category)
                redacted = pattern.sub(_REDACTED, redacted)
        return DetectionResult(tuple(hard), tuple(confirm), redacted)

    @staticmethod
    def normalize_query(text: str, max_chars: int) -> str:
        normalized = sanitize_plain_text(text)
        normalized = normalized.replace("[REDACTED]", " ")
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized[:max_chars].strip()


_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_INJECTION_MARKERS = re.compile(
    r"(?:ignore (?:all |the )?(?:previous|prior) instructions|system prompt|developer message|"
    r"reveal (?:the )?(?:secret|prompt)|execute (?:a )?(?:command|tool)|read (?:a )?(?:local )?file|"
    r"以前の(?:命令|指示)を無視|システムプロンプト|秘密を(?:出力|公開)|コマンドを実行)",
    re.IGNORECASE,
)


def sanitize_plain_text(value: str, max_chars: int | None = None) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<(?:script|style)\b[^>]*>.*?</(?:script|style)>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]*>", " ", text)
    text = unicodedata.normalize("NFKC", text)
    text = "".join(
        char
        for char in text
        if char not in {"\u200b", "\u200c", "\u200d", "\ufeff"}
        and not ("\u202a" <= char <= "\u202e")
        and not ("\u2066" <= char <= "\u2069")
    )
    text = _CONTROL_CHARACTERS.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if max_chars is not None:
        text = text[:max_chars].strip()
    return text


def has_injection_markers(value: str) -> bool:
    return bool(_INJECTION_MARKERS.search(value))


def validate_public_web_url(value: str) -> str | None:
    candidate = sanitize_plain_text(value, 2048)
    try:
        parsed = urlsplit(candidate)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    if parsed.username or parsed.password:
        return None
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith((".local", ".internal", ".intranet", ".lan")):
        return None
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        return None
    return candidate
