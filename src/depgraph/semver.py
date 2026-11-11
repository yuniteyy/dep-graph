"""Minimal semver: versions and npm-style version ranges."""
import operator
import re
from dataclasses import dataclass
from functools import total_ordering

FULL = re.compile(
    r"[v=]*\s*(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?"
    r"(?:\+[0-9A-Za-z.-]+)?")
PARTIAL = re.compile(
    r"v?(\d+|[xX*])(?:\.(\d+|[xX*]))?(?:\.(\d+|[xX*]))?"
    r"(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?")
HYPHEN = re.compile(r"(\S+)\s+-\s+(\S+)")
OPERATOR_GAP = re.compile(r"(\^|~>|~|>=|<=|>|<|=)\s+")
TOKEN = re.compile(r"(\^|~>|~|>=|<=|>|<|=)?(.*)")
WILDCARDS = "xX*"
OR_SEPARATOR = "||"
PARTS = 3


class SemverError(ValueError):
    """A version or a range cannot be parsed."""


@total_ordering
@dataclass(frozen=True)
class Version:
    """A semantic version; build metadata is ignored."""

    major: int
    minor: int
    patch: int
    pre: tuple = ()

    def key(self):
        """Return a tuple that orders versions according to semver."""
        base = (self.major, self.minor, self.patch)
        if not self.pre:
            return (*base, 1, ())
        ids = tuple((0, int(item), "") if item.isdigit() else (1, 0, item)
                    for item in self.pre)
        return (*base, 0, ids)

    def __lt__(self, other):
        """Compare by semver precedence."""
        return self.key() < other.key()

    def triple(self):
        """Return ``(major, minor, patch)``."""
        return (self.major, self.minor, self.patch)


def parse_version(text):
    """Return the :class:`Version` for ``text`` or ``None`` if invalid."""
    match = FULL.fullmatch(text.strip())
    if not match:
        return None
    major, minor, patch, pre = match.groups()
    pre_ids = tuple(pre.split(".")) if pre else ()
    return Version(int(major), int(minor), int(patch), pre_ids)


ANY = ((">=", Version(0, 0, 0)),)
NOTHING = (("<", Version(0, 0, 0)),)


def _low(major, minor, patch, pre):
    """Build the lowest version of a partial, filling gaps with zero."""
    return Version(major, minor or 0, patch or 0, pre)


def _equal(major, minor, patch, pre):
    """Comparators of a bare or ``=`` partial (x-range)."""
    if major is None:
        return ANY
    if minor is None:
        return ((">=", Version(major, 0, 0)), ("<", Version(major + 1, 0, 0)))
    if patch is None:
        return ((">=", Version(major, minor, 0)),
                ("<", Version(major, minor + 1, 0)))
    return (("=", Version(major, minor, patch, pre)),)


def _tilde(major, minor, patch, pre):
    """Comparators of ``~`` (patch-level changes)."""
    if major is None:
        return ANY
    low = (">=", _low(major, minor, patch, pre))
    if minor is None:
        return (low, ("<", Version(major + 1, 0, 0)))
    return (low, ("<", Version(major, minor + 1, 0)))


def _caret_upper(major, minor, patch):
    """Exclusive upper bound of ``^`` for a non-wildcard major."""
    if major:
        return Version(major + 1, 0, 0)
    if minor is None:
        return Version(1, 0, 0)
    if minor:
        return Version(0, minor + 1, 0)
    if patch is None:
        return Version(0, 1, 0)
    return Version(0, 0, patch + 1)


def _caret(major, minor, patch, pre):
    """Comparators of ``^`` (changes that keep the left-most non-zero)."""
    if major is None:
        return ANY
    low = (">=", _low(major, minor, patch, pre))
    return (low, ("<", _caret_upper(major, minor, patch)))


def _greater(major, minor, patch, pre):
    """Comparators of ``>``."""
    if major is None:
        return NOTHING
    if minor is None:
        return ((">=", Version(major + 1, 0, 0)),)
    if patch is None:
        return ((">=", Version(major, minor + 1, 0)),)
    return ((">", Version(major, minor, patch, pre)),)


def _greater_equal(major, minor, patch, pre):
    """Comparators of ``>=``."""
    if major is None:
        return ANY
    return ((">=", _low(major, minor, patch, pre)),)


def _less(major, minor, patch, pre):
    """Comparators of ``<``."""
    if major is None:
        return NOTHING
    return (("<", _low(major, minor, patch, pre)),)


def _less_equal(major, minor, patch, pre):
    """Comparators of ``<=``."""
    if major is None:
        return ANY
    if minor is None:
        return (("<", Version(major + 1, 0, 0)),)
    if patch is None:
        return (("<", Version(major, minor + 1, 0)),)
    return (("<=", Version(major, minor, patch, pre)),)


DESUGAR = {
    None: _equal, "=": _equal, "^": _caret, "~": _tilde, "~>": _tilde,
    ">": _greater, ">=": _greater_equal, "<": _less, "<=": _less_equal,
}
COMPARE = {
    "=": operator.eq, ">": operator.gt, ">=": operator.ge,
    "<": operator.lt, "<=": operator.le,
}


def _parse_partial(text):
    """Split a partial version into ``(major, minor, patch, pre)``."""
    match = PARTIAL.fullmatch(text)
    if not match:
        raise SemverError(f"некорректная часть диапазона версий '{text}'")
    numbers = [None if group is None or group in WILDCARDS else int(group)
               for group in match.groups()[:PARTS]]
    major, minor, patch = numbers
    if major is None:
        minor = patch = None
    if minor is None:
        patch = None
    pre = match.group(PARTS + 1)
    return major, minor, patch, (tuple(pre.split(".")) if pre else ())


def _parse_set(text):
    """Parse space-separated comparators (logical AND)."""
    text = text.strip()
    hyphen = HYPHEN.fullmatch(text)
    if hyphen:
        low, high = hyphen.groups()
        return (*_greater_equal(*_parse_partial(low)),
                *_less_equal(*_parse_partial(high)))
    comparators = []
    for word in OPERATOR_GAP.sub(r"\1", text).split():
        sign, rest = TOKEN.fullmatch(word).groups()
        comparators.extend(DESUGAR[sign](*_parse_partial(rest)))
    return tuple(comparators) or ANY


def parse_range(text):
    """Parse an npm range into a tuple of comparator sets (logical OR)."""
    return tuple(_parse_set(part) for part in text.split(OR_SEPARATOR))


def _set_allows(version, comparators):
    """Tell whether ``version`` satisfies one set of comparators."""
    for sign, bound in comparators:
        if not COMPARE[sign](version, bound):
            return False
    if not version.pre:
        return True
    return any(bound.pre and bound.triple() == version.triple()
               for _, bound in comparators)


def satisfies(version_text, range_text):
    """Tell whether the version string satisfies the range string."""
    version = parse_version(version_text)
    if version is None:
        return False
    return any(_set_allows(version, comparators)
               for comparators in parse_range(range_text))


def max_satisfying(candidates, range_text):
    """Return the highest of ``candidates`` inside the range, or ``None``."""
    ranges = parse_range(range_text)
    best_text, best = None, None
    for text in candidates:
        version = parse_version(text)
        if version is None:
            continue
        if any(_set_allows(version, item) for item in ranges):
            if best is None or version > best:
                best_text, best = text, version
    return best_text
