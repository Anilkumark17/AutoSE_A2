"""Hidden acceptance tests for T1. Do not copy these into either condition."""

import unittest

import markdown


def _ids(tokens):
    found = []
    for token in tokens:
        found.append(token["id"])
        found.extend(_ids(token.get("children") or []))
    return found


class EmptyHeadingIds(unittest.TestCase):
    def test_single_empty_slug_heading(self):
        md = markdown.Markdown(extensions=["toc"])
        html = md.convert("# !!!\n\n[TOC]\n")
        self.assertEqual(
            html,
            "<h1 id=\"_1\">!!!</h1>\n"
            "<div class=\"toc\">\n"
            "<ul>\n"
            "<li><a href=\"#_1\">!!!</a></li>\n"
            "</ul>\n"
            "</div>",
        )
        self.assertEqual(_ids(md.toc_tokens), ["_1"])

    def test_several_empty_slugs_share_the_duplicate_numbering(self):
        md = markdown.Markdown(extensions=["toc"])
        html = md.convert("# !!!\n\n[TOC]\n\n## ???\n")
        self.assertIn('<h1 id="_1">!!!</h1>', html)
        self.assertIn('<h2 id="_2">???</h2>', html)
        self.assertIn('<a href="#_1">!!!</a>', html)
        self.assertIn('<a href="#_2">???</a>', html)
        self.assertNotIn('id=""', html)
        self.assertNotIn('href="#"', html)
        self.assertEqual(_ids(md.toc_tokens), ["_1", "_2"])

    def test_ordinary_ids_stay_put_and_taken_ids_are_not_reused(self):
        md = markdown.Markdown(extensions=["toc"])
        html = md.convert("# foo\n\n# foo\n\n# !!!\n\n# bar\n\n[TOC]\n")
        self.assertIn('<h1 id="foo">foo</h1>', html)
        self.assertIn('<h1 id="foo_1">foo</h1>', html)
        self.assertIn('<h1 id="_1">!!!</h1>', html)
        self.assertIn('<h1 id="bar">bar</h1>', html)
        self.assertEqual(_ids(md.toc_tokens), ["foo", "foo_1", "_1", "bar"])

        taken = markdown.Markdown(extensions=["toc", "attr_list"])
        taken_html = taken.convert("# Keep {#_1}\n\n# !!!\n\n[TOC]\n")
        self.assertIn('<h1 id="_1">Keep</h1>', taken_html)
        self.assertIn('<h1 id="_2">!!!</h1>', taken_html)
        self.assertEqual(taken_html.count('id="_1"'), 1)
        self.assertEqual(_ids(taken.toc_tokens), ["_1", "_2"])

    def test_numbering_restarts_after_reset(self):
        md = markdown.Markdown(extensions=["toc"])
        first = md.convert("# !!!\n\n# !!!\n")
        self.assertIn('<h1 id="_1">!!!</h1>', first)
        self.assertIn('<h1 id="_2">!!!</h1>', first)
        md.reset()
        second = md.convert("# ???\n")
        self.assertIn('<h1 id="_1">???</h1>', second)
        self.assertNotIn('id="_2"', second)
        self.assertNotIn('id="_3"', second)


if __name__ == "__main__":
    unittest.main()
