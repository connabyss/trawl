"""Reading Trawl source: tokens, the syntax tree, and the list of built-in words.

Trawl reads exactly like the Tide programs it grew out of, so every old .tide file
still means the same thing. The tree is shared by the reference interpreter
(trawl/interp.py) and the native compiler (trawl/cgen.py).
"""
import difflib
import os
import re
from dataclasses import dataclass, field

# Every built-in word, grouped the way the spec (docs/SPEC.md) lists them.
ARITH = ["+", "-", "*", "/", "%", "=", "<", ">"]
STACK = ["dup", "drop", "swap", "over", "rot", "fold", "depth"]
OUTPUT = [".", "emit", ".s", ".bed", ".pearls"]
SEABED = ["bury", "dig", "drain"]
NUMBERS = ["digsum", "altsum", "power", "prime", "spf", "factorings"]
# built-ins added after Tide: old programs that defined their own word by one of these names keep it
YOURS_WINS = {"prime", "spf", "factorings"}
ECHO = ["echo", "hush"]
WORLDS = ["wave", "want", "more", "aim", "worlds"]
SYNTAX = ["if", "else", "then", "[", "]", ":", ";", "use", "pearl", "sweep"]
BUILTINS = ARITH + STACK + OUTPUT + SEABED + NUMBERS + ECHO + WORLDS + SYNTAX

# How many numbers each word takes off the stack (for error messages and the compiler).
WANTS = {**{w: 2 for w in ARITH}, "dup": 1, "drop": 1, "swap": 2, "over": 2, "rot": 3,
         ".": 1, "emit": 1, "bury": 2, "dig": 1, "digsum": 2, "altsum": 2, "power": 2, "prime": 1, "spf": 1, "factorings": 1,
         "echo": 2, "wave": 2, "want": 1, "aim": 1, "if": 1, "sweep": 2}

EXTENSIONS = (".trawl", ".tide")
LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")


class TrawlError(Exception):
    """Something the sea refuses. The message is meant for a person."""


@dataclass
class Tok:
    text: str
    line: int
    file: str


@dataclass
class Num:
    value: int
    tok: Tok


@dataclass
class Word:
    name: str
    tok: Tok


@dataclass
class Text:
    text: str
    tok: Tok


@dataclass
class If:
    then: list
    other: list  # None when there is no else
    tok: Tok


@dataclass
class Loop:
    body: list
    tok: Tok


@dataclass
class Def:
    name: str
    body: list
    tok: Tok


@dataclass
class PearlDecl:
    name: str
    tok: Tok


@dataclass
class Sweep:
    """`lo hi sweep name`: run name on every n from lo up to hi - 1 and count the nonzero answers."""
    name: str
    tok: Tok


@dataclass
class Program:
    body: list
    defs: list = field(default_factory=list)  # every Def, in the order they appear


NUMBER = re.compile(r"[+-]?\d+(?:_\d+)*\Z", re.ASCII)  # 0-9 only, as the spec says


def tokens(src, file="<program>"):
    """Split source into tokens. `#` starts a comment, except on a line that also holds `."` text."""
    src = "\n".join(line.split("#", 1)[0] if '."' not in line else line for line in src.splitlines())
    out = []
    for m in re.finditer(r'\."[^"]*"|\S+', src):
        out.append(Tok(m.group(), src.count("\n", 0, m.start()) + 1, file))
    return out


def where(tok):
    return f"{os.path.basename(tok.file)}:{tok.line}"


def find_lib(name, search, flat=False):
    """flat: every library sits in one folder under its own file name (a receipt being checked)."""
    if flat:
        name = re.split(r"[\\/]", name)[-1]
    for d in search:
        for ext in EXTENSIONS:
            p = os.path.join(d, name + ext)
            if os.path.isfile(p):
                return p
    return None


def expand(toks, search, depth=0, used=None, flat=False, chain=()):
    """Replace every `use name` with the tokens of name.trawl (or name.tide).
    `used`, if given, collects the path of every library file read."""
    out, i = [], 0
    while i < len(toks):
        t = toks[i]
        if t.text == "use":
            if i + 1 >= len(toks):
                raise TrawlError(f"{where(t)}: `use` needs the name of a library after it")
            name = toks[i + 1].text
            path = find_lib(name, search, flat)
            if path is None:
                raise TrawlError(f"{where(t)}: no library called `{name}` (looked for {name}.trawl and {name}.tide)")
            if os.path.abspath(path) in chain or depth > 50:  # the `use` that closes the circle is named
                names = [os.path.basename(c) for c in chain] + [os.path.basename(path)]
                raise TrawlError(f"{where(t)}: libraries keep using each other in a circle ({' -> '.join(names)})")
            here = [os.path.dirname(os.path.abspath(path))] + search
            if used is not None and path not in used:
                used.append(path)
            out += expand(tokens(read_source(path), path), here, depth + 1, used, flat, chain + (os.path.abspath(path),))
            i += 2
        else:
            out.append(t)
            i += 1
    return out


class Parser:
    def __init__(self, toks):
        self.toks, self.i, self.defs = toks, 0, []

    def block(self, closers, opener=None):
        body = []
        while self.i < len(self.toks):
            t = self.toks[self.i]
            s = t.text
            if s in closers:
                return body, s
            self.i += 1
            if s == ":":
                body.append(self.definition(t))
            elif s == "[":
                inner, _ = self.block(["]"], t)
                self.i += 1
                body.append(Loop(inner, t))
            elif s == "if":
                then, end = self.block(["else", "then"], t)
                self.i += 1
                other = None
                if end == "else":
                    other, _ = self.block(["then"], t)
                    self.i += 1
                body.append(If(then, other, t))
            elif s == "pearl":
                if self.i >= len(self.toks):
                    raise TrawlError(f"{where(t)}: `pearl` needs the name of a word after it")
                body.append(PearlDecl(self.toks[self.i].text, t))
                self.i += 1
            elif s == "sweep":
                name = self.toks[self.i].text if self.i < len(self.toks) else None
                if name in ("prime", "spf", "factorings"):
                    raise TrawlError(
                        f"{where(t)}: `sweep` takes one of your own words, and `{name}` is built in. "
                        f"Wrap it first: `: {name}? {name} ;` then use `sweep {name}?` with your bounds."
                    )
                if name is None or name in BUILTINS or NUMBER.match(name):
                    raise TrawlError(f"{where(t)}: `sweep` needs the name of one of your words after it, like `1 1000 sweep good?`")
                body.append(Sweep(name, t))
                self.i += 1
            elif s in ("]", "else", "then", ";"):
                raise TrawlError(f"{where(t)}: a stray `{s}` with nothing open for it to close")
            elif s.startswith('."') and len(s) >= 3 and s.endswith('"'):
                body.append(Text(s[2:-1].lstrip(), t))
            elif s.startswith('."'):
                raise TrawlError(f"{where(t)}: this `.\"` text never closes. end it with a `\"`")
            elif NUMBER.match(s):
                body.append(Num(int(s), t))
            else:
                body.append(Word(s, t))
        if opener is not None:
            raise TrawlError(f"{where(opener)}: a `{opener.text}` was opened and the sea never closed it")
        return body, None

    def definition(self, colon):
        if self.i >= len(self.toks):
            raise TrawlError(f"{where(colon)}: `:` needs a name and a body ending in `;`")
        name_tok = self.toks[self.i]
        name = name_tok.text
        if name in BUILTINS and name not in YOURS_WINS:
            raise TrawlError(f"{where(name_tok)}: `{name}` is a word of the sea itself. pick another name.")
        if NUMBER.match(name):
            raise TrawlError(f"{where(name_tok)}: `{name}` is a number, so it can't be a word's name")
        self.i += 1
        body, end = self.block([";"])
        if end is None:
            raise TrawlError(f"{where(colon)}: the definition of `{name}` never reached its `;`")
        self.i += 1
        d = Def(name, body, colon)
        self.defs.append(d)
        return d


def read_source(path):
    """A program or library file as text: UTF-8, with or without a byte-order mark."""
    with open(path, "rb") as fh:
        data = fh.read()
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise TrawlError(f"{os.path.basename(path)} isn't UTF-8 text (byte {e.start + 1} is {data[e.start]:#04x}). "
                         "save it as UTF-8 and try again") from None


def parse(src, file="<program>", search=None, used=None, flat=False):
    """Source text -> Program. `search` lists folders for `use`; the program's folder and lib/ are added.
    `used`, if given, collects the path of every library file read."""
    dirs = list(search or [])
    if file and file != "<program>":
        dirs.insert(0, os.path.dirname(os.path.abspath(file)))
    dirs.append(LIB_DIR)
    if src.startswith("\ufeff"):  # a byte-order mark some editors put first
        src = src[1:]
    p = Parser(expand(tokens(src, file), dirs, used=used, flat=flat))
    body, _ = p.block([])
    return Program(body, p.defs)


def shown(name):
    """A word as an error message shows it: invisible characters (a NUL, an escape) written as \\xNN."""
    return "".join(f"\\x{ord(c):02x}" if ord(c) < 32 or ord(c) == 127 else c for c in name)


def special_hint(name):
    """A hint for a word that isn't a misspelling: a `#` that isn't a comment, or a number that isn't whole."""
    if name.startswith("#"):
        return " on a line with `.\"` text, `#` isn't a comment. put the comment on its own line"
    if re.fullmatch(r"[+-]?(\d[\d_]*)?\.\d+|[+-]?\d[\d_]*\.\d*|[+-]?\d[\d_]*(\.\d*)?[eE][+-]?\d+", name):
        return " Trawl's numbers are all whole: no decimal points or exponents"
    return None


def suggest(name, known):
    hint = special_hint(name)
    if hint:
        return hint
    near = difflib.get_close_matches(name, list(BUILTINS) + list(known), 1, 0.6)
    return f" did you mean `{near[0]}`?" if near else ""
