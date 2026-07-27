import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parent))
import ruby_css_verifier as verifier  # noqa: E402


class ParseRubiesTests(unittest.TestCase):
    def test_parses_case_newlines_quotes_and_br_variants(self):
        content = """
<ruby>radik<rt class="S_S">root<br>note</rt></ruby>
<RUBY data-kind="formatted">
  PRI
  <RT
    data-lang="ja"
    data-class="ignored"
    class='M_M'
  >before<BR/>after</RT>
</RUBY>
<ruby>lim<rt class=“L_L”>boundary</rt></ruby>
"""

        parsed = verifier.parse_rubies(content)

        self.assertEqual(verifier.count_raw_ruby_opens(content), 3)
        self.assertEqual(len(parsed), 3)
        self.assertEqual(parsed[0][1:6], ("radik", "S_S", "root<br>note", "rootnote", False))
        self.assertEqual(parsed[1][1:6], ("PRI", "M_M", "before<BR/>after", "beforeafter", False))
        self.assertEqual(parsed[2][1:6], ("lim", "L_L", "boundary", "boundary", True))

    def test_raw_count_exposes_unsupported_class_markup(self):
        content = (
            '<ruby>a<rt class="L_L">x</rt></ruby>'
            '<RUBY>bad<RT class=L_L>y</RT></RUBY>'
        )

        self.assertEqual(verifier.count_raw_ruby_opens(content), 2)
        self.assertEqual(len(verifier.parse_rubies(content)), 1)


class VerifyFileTests(unittest.TestCase):
    width_data = {"a": 4, "x": 6}

    def test_reports_raw_parsed_gap(self):
        content = (
            '<ruby>a<rt class="L_L">x</rt></ruby>'
            '<ruby>bad<rt class=L_L>y</rt></ruby>'
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "gap.html")
            path.write_text(content, encoding="utf-8")
            stdout = io.StringIO()
            with mock.patch.object(verifier, "_load_width_data", return_value=self.width_data):
                with contextlib.redirect_stdout(stdout):
                    result = verifier.verify_file(path)

        self.assertEqual(result, 1)
        report = stdout.getvalue()
        self.assertIn("Raw ruby opens: 2   Parsed ruby: 1   Unparsed: 1", report)
        self.assertIn("WARNING: 1 ruby tag(s) could not be parsed", report)

    def test_smart_quote_normalization_is_fixable_at_boundary(self):
        # ratio 6/4 == 1.5, exactly on a threshold; M_M -> L_L would
        # ordinarily be skipped with margin=0.05.
        content = '<ruby>a<rt class=“M_M”>x</rt></ruby>'
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "smart.html")
            path.write_text(content, encoding="utf-8")
            stdout = io.StringIO()
            with mock.patch.object(verifier, "_load_width_data", return_value=self.width_data):
                with contextlib.redirect_stdout(stdout):
                    result = verifier.verify_file(str(path), fix=True, margin=0.05)
            fixed = path.read_text(encoding="utf-8")

        self.assertEqual(result, 1)
        self.assertEqual(fixed, '<ruby>a<rt class="L_L">x</rt></ruby>')
        self.assertIn("Margin: 0.05  Fixable: 1  Boundary(skip): 0", stdout.getvalue())

    def test_same_class_wrong_break_is_fixable_and_preserves_attributes(self):
        # xxxx/a has ratio 6.0, hence XXS_S with the break after the second x.
        # Threshold proximity must not hide an independently wrong break.
        content = (
            '<ruby data-kind="formatted">a'
            '<rt data-lang="ja" class="XXS_S" aria-label="note">'
            'xxx<br>x</rt></ruby>'
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "break.html")
            path.write_text(content, encoding="utf-8")
            stdout = io.StringIO()
            with mock.patch.object(verifier, "_load_width_data", return_value=self.width_data):
                with contextlib.redirect_stdout(stdout):
                    result = verifier.verify_file(
                        str(path), fix=True, margin=0.05
                    )
            fixed = path.read_text(encoding="utf-8")

        self.assertEqual(result, 1)
        self.assertEqual(
            fixed,
            '<ruby data-kind="formatted">a'
            '<rt data-lang="ja" class="XXS_S" aria-label="note">'
            'xx<br>xx</rt></ruby>',
        )
        report = stdout.getvalue()
        self.assertIn(
            "class=0  break=1  break-only=1  smart-quote=0", report
        )
        self.assertIn("Margin: 0.05  Fixable: 1  Boundary(skip): 0", report)
        self.assertIn("Break-placement mismatches: 1 instances", report)
        self.assertIn(
            "Post-fix: 0 total mismatches "
            "(0 boundary, 0 break, 0 break-only, 0 real)",
            report,
        )

    def test_margin_still_skips_adjacent_class_boundary(self):
        # ratio 6/4 == 1.5: expected L_L, current M_M is an adjacent class
        # exactly at a threshold and therefore remains a boundary skip.
        content = '<ruby>a<rt class="M_M">x</rt></ruby>'
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "boundary.html")
            path.write_text(content, encoding="utf-8")
            stdout = io.StringIO()
            with mock.patch.object(verifier, "_load_width_data", return_value=self.width_data):
                with contextlib.redirect_stdout(stdout):
                    result = verifier.verify_file(
                        str(path), fix=True, margin=0.05
                    )
            unchanged = path.read_text(encoding="utf-8")

        self.assertEqual(result, 1)
        self.assertEqual(unchanged, content)
        self.assertIn("Margin: 0.05  Fixable: 0  Boundary(skip): 1", stdout.getvalue())

    def test_boundary_class_is_retained_while_its_break_is_fixed(self):
        # xxxx/aa has ratio 3.0, exactly at the XS_S/XXS_S boundary.
        # Retain the current adjacent XXS_S class, but normalize the break
        # according to that retained class.
        content = (
            '<ruby data-kind="formatted">aa'
            '<rt data-lang="ja" class="XXS_S" aria-label="note">'
            'xxx<br>x</rt></ruby>'
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "boundary_break.html")
            path.write_text(content, encoding="utf-8")
            stdout = io.StringIO()
            with mock.patch.object(verifier, "_load_width_data", return_value=self.width_data):
                with contextlib.redirect_stdout(stdout):
                    result = verifier.verify_file(
                        str(path), fix=True, margin=0.05
                    )
            fixed = path.read_text(encoding="utf-8")

        self.assertEqual(result, 1)
        self.assertEqual(
            fixed,
            '<ruby data-kind="formatted">aa'
            '<rt data-lang="ja" class="XXS_S" aria-label="note">'
            'xx<br>xx</rt></ruby>',
        )
        report = stdout.getvalue()
        self.assertIn(
            "class=1  break=1  break-only=0  smart-quote=0", report
        )
        self.assertIn("Margin: 0.05  Fixable: 1  Boundary(skip): 1", report)
        self.assertIn(
            "Post-fix: 1 total mismatches "
            "(1 boundary, 0 break, 0 break-only, 0 real)",
            report,
        )

    def test_break_only_mismatch_is_not_reported_as_boundary(self):
        content = '<ruby>a<rt class="XXS_S">xxx<br>x</rt></ruby>'
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "break_only.html")
            path.write_text(content, encoding="utf-8")
            stdout = io.StringIO()
            with mock.patch.object(verifier, "_load_width_data", return_value=self.width_data):
                with contextlib.redirect_stdout(stdout):
                    result = verifier.verify_file(
                        str(path), boundary_only=True
                    )

        self.assertEqual(result, 1)
        self.assertIn("Boundary cases: 0 instances", stdout.getvalue())

    def test_fix_preserves_ruby_and_non_class_rt_attributes(self):
        content = (
            '<ruby data-kind="formatted">a'
            '<rt data-lang="ja" class="M_M" aria-label="note">x</rt></ruby>'
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "attributes.html")
            path.write_text(content, encoding="utf-8")
            with mock.patch.object(verifier, "_load_width_data", return_value=self.width_data):
                with contextlib.redirect_stdout(io.StringIO()):
                    result = verifier.verify_file(str(path), fix=True)
            fixed = path.read_text(encoding="utf-8")

        self.assertEqual(result, 1)
        self.assertEqual(
            fixed,
            '<ruby data-kind="formatted">a'
            '<rt data-lang="ja" class="L_L" aria-label="note">x</rt></ruby>',
        )

    def test_cli_returns_nonzero_for_unparsed_ruby(self):
        content = '<ruby>bad<rt class=L_L>x</rt></ruby>'
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "unparsed.html")
            path.write_text(content, encoding="utf-8")
            argv = ["ruby_css_verifier.py", str(path)]
            with mock.patch.object(sys, "argv", argv):
                with mock.patch.object(verifier, "_load_width_data", return_value=self.width_data):
                    with contextlib.redirect_stdout(io.StringIO()):
                        result = verifier.main()

        self.assertEqual(result, 1)


if __name__ == "__main__":
    unittest.main()
