"""Tests for versions and npm-style ranges."""
import unittest

from depgraph.semver import (
    SemverError, max_satisfying, parse_version, satisfies)

MATCH = {
    "^1.2.3": ["1.2.3", "1.9.9"],
    "^0.2.3": ["0.2.3", "0.2.9"],
    "^0.0.3": ["0.0.3"],
    "^1.2": ["1.2.0", "1.8.0"],
    "^0.0": ["0.0.7"],
    "~1.2.3": ["1.2.3", "1.2.99"],
    "~1.2": ["1.2.0", "1.2.5"],
    "~1": ["1.0.0", "1.9.9"],
    "1.x": ["1.0.0", "1.4.4"],
    "1.2.x": ["1.2.0", "1.2.8"],
    "1.2.*": ["1.2.3"],
    "*": ["0.0.1", "9.9.9"],
    "": ["1.0.0"],
    "x": ["2.3.4"],
    "1.2.3": ["1.2.3"],
    "=1.2.3": ["1.2.3"],
    ">=1.2.3 <2.0.0": ["1.2.3", "1.9.0"],
    ">1.2.3": ["1.2.4", "2.0.0"],
    ">= 1.2.3": ["1.2.3"],
    "<=2": ["2.9.9", "0.1.0"],
    "<1.5": ["1.4.9"],
    "1.2.3 - 2.3.4": ["1.2.3", "2.3.4", "2.0.0"],
    "1.2 - 2.3": ["1.2.0", "2.3.9"],
    "^1.0.0 || ^3.0.0": ["1.5.0", "3.1.0"],
    "^1.2.3-beta.2": ["1.2.3-beta.4", "1.2.3", "1.5.0"],
    ">=1.0.0-alpha <1.0.0": ["1.0.0-beta"],
}
NO_MATCH = {
    "^1.2.3": ["1.2.2", "2.0.0", "2.0.0-beta"],
    "^0.2.3": ["0.3.0", "0.2.2"],
    "^0.0.3": ["0.0.4"],
    "~1.2.3": ["1.3.0", "1.2.2"],
    "~1": ["2.0.0", "0.9.9"],
    "1.x": ["2.0.0"],
    "*": ["1.0.0-alpha"],
    "1.2.3": ["1.2.4"],
    ">=1.2.3 <2.0.0": ["2.0.0", "1.2.2"],
    ">1.2.3": ["1.2.3"],
    "1.2.3 - 2.3.4": ["2.3.5", "1.2.2"],
    "^1.0.0 || ^3.0.0": ["2.0.0"],
    ">=1.0.0": ["2.0.0-beta"],
    "^1.2.3-beta.2": ["1.2.3-beta.1", "1.2.4-beta.1"],
}


class VersionTests(unittest.TestCase):
    """Parsing and ordering of versions."""

    def test_parse(self):
        """Release, pre-release and build forms are parsed."""
        self.assertEqual(parse_version("1.2.3").triple(), (1, 2, 3))
        self.assertEqual(parse_version("v1.2.3-rc.1+b5").pre, ("rc", "1"))
        self.assertIsNone(parse_version("1.2"))
        self.assertIsNone(parse_version("latest"))

    def test_precedence(self):
        """The ordering follows the semver specification."""
        order = ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta",
                 "1.0.0-beta", "1.0.0-beta.2", "1.0.0-beta.11",
                 "1.0.0-rc.1", "1.0.0", "1.0.1", "1.1.0", "2.0.0"]
        parsed = [parse_version(item) for item in order]
        self.assertEqual(sorted(parsed, reverse=True)[::-1], parsed)
        self.assertEqual(sorted(parsed), parsed)

    def test_numeric_not_lexicographic(self):
        """10 is greater than 9."""
        self.assertGreater(parse_version("1.10.0"), parse_version("1.9.0"))


class RangeTests(unittest.TestCase):
    """Matching versions against ranges."""

    def test_matching_versions(self):
        """Every listed version satisfies its range."""
        for spec, versions in MATCH.items():
            for version in versions:
                self.assertTrue(satisfies(version, spec), (spec, version))

    def test_non_matching_versions(self):
        """No listed version satisfies its range."""
        for spec, versions in NO_MATCH.items():
            for version in versions:
                self.assertFalse(satisfies(version, spec), (spec, version))

    def test_invalid_ranges(self):
        """Things that are not ranges raise SemverError."""
        for spec in ("latest", "git+https://x/y.git", "user/repo",
                     "file:../x", "^^1", "1.2.3.4"):
            with self.assertRaises(SemverError, msg=spec):
                satisfies("1.0.0", spec)

    def test_invalid_candidate(self):
        """An unparsable version never satisfies anything."""
        self.assertFalse(satisfies("oops", "*"))


class MaxSatisfyingTests(unittest.TestCase):
    """Choosing the highest matching version."""

    VERSIONS = ["1.0.0", "1.2.0", "1.10.0", "2.0.0", "2.1.0-beta", "bad"]

    def test_highest_in_range(self):
        """The highest satisfying version wins (numeric comparison)."""
        self.assertEqual(max_satisfying(self.VERSIONS, "^1.0.0"), "1.10.0")
        self.assertEqual(max_satisfying(self.VERSIONS, "~1.2.0"), "1.2.0")

    def test_star_skips_prereleases(self):
        """``*`` does not select pre-releases."""
        self.assertEqual(max_satisfying(self.VERSIONS, "*"), "2.0.0")

    def test_none(self):
        """No satisfying version gives ``None``."""
        self.assertIsNone(max_satisfying(self.VERSIONS, "^5.0.0"))
