"""Tests for the test repository file format."""
import os
import tempfile
import unittest
from pathlib import Path

from depgraph.testrepo import FileRepository, TestRepoError

REPOS = Path(__file__).resolve().parent.parent / "examples" / "repos"


def load_text(text):
    """Load a repository from a string through a temporary file."""
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "repo.txt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return FileRepository.load(path)


class LoadTests(unittest.TestCase):
    """Reading valid files."""

    def test_simple_example(self):
        """The bundled example is read correctly."""
        repo = FileRepository.load(REPOS / "simple.txt")
        self.assertEqual(repo.dependencies("A"), ["B", "C"])
        self.assertEqual(repo.dependencies("C"), ["D", "E"])
        self.assertEqual(repo.dependencies("D"), [])

    def test_comments_commas_and_blank_lines(self):
        """Comments and blank lines are ignored; commas separate."""
        repo = load_text("# c\n\nA: B, C  # tail\nB:\n")
        self.assertEqual(repo.dependencies("A"), ["B", "C"])

    def test_duplicate_dependencies_are_merged(self):
        """A repeated dependency in one line counts once."""
        self.assertEqual(load_text("A: B B C\n").dependencies("A"),
                         ["B", "C"])

    def test_mentioned_package_is_a_leaf(self):
        """A package that is only a dependency has no dependencies."""
        repo = FileRepository.load(REPOS / "undefined.txt")
        self.assertTrue(repo.has("X"))
        self.assertEqual(repo.dependencies("X"), [])
        self.assertFalse(repo.has("Q"))

    def test_multi_letter_names(self):
        """Names may consist of several upper-case letters."""
        self.assertEqual(load_text("AB: CD\n").dependencies("AB"), ["CD"])

    def test_reversed(self):
        """Inversion lists the dependents of every package."""
        inverted = FileRepository.load(REPOS / "simple.txt").reversed()
        self.assertEqual(inverted.dependencies("D"), ["B", "C"])
        self.assertEqual(inverted.dependencies("A"), [])
        self.assertEqual(inverted.dependencies("E"), ["C"])


class ErrorTests(unittest.TestCase):
    """Reading broken files."""

    def assert_error(self, name, text):
        """Loading ``invalid/name`` fails mentioning ``text``."""
        with self.assertRaises(TestRepoError) as caught:
            FileRepository.load(REPOS / "invalid" / name)
        self.assertIn(text, str(caught.exception))

    def test_lowercase(self):
        """Lower-case names are rejected with the line number."""
        self.assert_error("lowercase.txt", "строка 2")

    def test_no_colon(self):
        """A line without a colon is rejected."""
        self.assert_error("no_colon.txt", "нет ':'")

    def test_duplicate(self):
        """A package defined twice is rejected."""
        self.assert_error("duplicate.txt", "повторно")

    def test_bad_dependency_name(self):
        """A malformed dependency name is rejected."""
        self.assert_error("bad_dependency.txt", "'b1'")

    def test_unreadable(self):
        """A missing file is reported."""
        with self.assertRaises(TestRepoError):
            FileRepository.load("/no/such/repo.txt")
