from .base import StatementParser
from .tangerine import TangerineParser

# Order matters: first parser whose detect() matches wins; generic is the fallback.
PARSERS = [TangerineParser]


def pick_parser(text: str) -> StatementParser:
    for cls in PARSERS:
        if cls.detect(text):
            return cls()
    return StatementParser()
