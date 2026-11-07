from .base import StatementParser
from .scotiabank import ScotiabankParser
from .tangerine import TangerineParser

# Order matters: first parser whose detect() matches wins; generic is the fallback.
PARSERS = [TangerineParser, ScotiabankParser]


def pick_parser(text: str) -> StatementParser:
    for cls in PARSERS:
        if cls.detect(text):
            return cls()
    return StatementParser()
