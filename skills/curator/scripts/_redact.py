"""Secrets out of everything the curator writes down: a string that looks like a credential becomes ``***``.

Transcripts hold what the person pasted and what commands printed, so a token can sit in a user turn, a command line
or an error. Every text the curator stores (figures, report, proposals it validates) or prints (``show``) goes
through ``redact`` first. It errs on the side of removing: a value that only looks like a secret goes too.
Standard library only.
"""

from __future__ import annotations

import re

MASK = "***"

_PEM = re.compile(
    r"-----BEGIN (?P<kind>[A-Z0-9 ]*?)PRIVATE KEY-----(?:[\s\S]*?-----END (?P=kind)PRIVATE KEY-----|[\s\S]*\Z)"
)
_SECRET_WORDS = r"TOKEN|SECRET|PASSWORD|PASSWD|PASSPHRASE|API_?KEY|ACCESS_?KEY|SECRET_?KEY|PRIVATE_?KEY|CREDENTIALS?"
# The value of a variable or key whose name says it holds a secret: GITHUB_TOKEN=..., "client_secret": "...".
_NAMED = re.compile(
    r"""
    (?P<head>
        (?:\b[A-Z][A-Z0-9_]*?(?:"""
    + _SECRET_WORDS
    + r""")[A-Z0-9_]*\b
          |["']?\b(?i:[a-z0-9_]*?(?:token|secret|password|passwd|passphrase|api_?key|access_?key|secret_?key
                |private_?key|client_secret))["']?)
        \s*[=:]\s*
        (?P<quote>["']?)
    )
    (?!\*\*\*)[^\s"'`,;&|)}\]]{6,}
    """,
    re.VERBOSE,
)
PATTERNS: tuple[tuple[re.Pattern, str], ...] = (
    # Anthropic API keys and OAuth tokens
    (re.compile(r"\b(?P<head>sk-ant-)[A-Za-z0-9_-]{8,}"), r"\g<head>" + MASK),
    # OpenAI keys: sk-, sk-proj-, sk-svcacct-
    (re.compile(r"\b(?P<head>sk-)(?!ant-)[A-Za-z0-9_-]{20,}"), r"\g<head>" + MASK),
    # GitHub tokens of every kind
    (re.compile(r"\b(?P<head>gh[pousr]_)[A-Za-z0-9]{20,}"), r"\g<head>" + MASK),
    (re.compile(r"\b(?P<head>github_pat_)[A-Za-z0-9_]{20,}"), r"\g<head>" + MASK),
    # GitLab personal tokens
    (re.compile(r"\b(?P<head>glpat-)[A-Za-z0-9_-]{16,}"), r"\g<head>" + MASK),
    # AWS access key ids
    (re.compile(r"\b(?:AKIA|ASIA|ABIA|ACCA|A3T[A-Z0-9])[A-Z0-9]{16}\b"), MASK),
    # Slack tokens
    (re.compile(r"\b(?P<head>xox[abposr]-)[A-Za-z0-9-]{10,}"), r"\g<head>" + MASK),
    # Google API keys
    (re.compile(r"\bAIza[0-9A-Za-z_-]{35}"), MASK),
    # JSON web tokens
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"), MASK),
    # Bearer and Basic credentials
    (re.compile(r"(?P<head>\bBearer\s+)[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE), r"\g<head>" + MASK),
    (re.compile(r"(?P<head>\bAuthorization\s*:\s*Basic\s+)[A-Za-z0-9+/=]{8,}", re.IGNORECASE), r"\g<head>" + MASK),
    # The password of a URI: scheme://user:password@host
    (re.compile(r"(?P<head>\b[a-z][a-z0-9+.-]*://[^\s/:@]+:)[^\s/@]{3,}(?=@)", re.IGNORECASE), r"\g<head>" + MASK),
    # Credential query parameters
    (
        re.compile(r"(?P<head>[?&](?:access_token|token|api_key|apikey|key|sig|signature|password)=)[^&\s]{6,}", re.I),
        r"\g<head>" + MASK,
    ),
    (_NAMED, r"\g<head>" + MASK),
)


def redact(text: str) -> str:
    """``text`` with every value that looks like a secret replaced by MASK."""
    if not text:
        return text
    text = _PEM.sub(lambda found: f"-----BEGIN {found['kind']}PRIVATE KEY-----{MASK}", text)
    for pattern, replacement in PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def redact_data(value):
    """A copy of a JSON value with every string in it redacted."""
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, list):
        return [redact_data(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_data(item) for key, item in value.items()}
    return value
