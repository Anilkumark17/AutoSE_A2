"""Hidden acceptance tests for T2. Do not copy these into either condition."""

import unittest

import markdown


def _render(source):
    return markdown.markdown(source, extensions=["admonition"])


class CollapsibleAdmonitions(unittest.TestCase):
    def test_question_mark_marker_renders_details_with_inline_markdown(self):
        html = _render('??? note "Hello"\n\n    Body *em*.\n')
        self.assertEqual(
            html,
            '<details class="admonition note">\n'
            '<summary class="admonition-title">Hello</summary>\n'
            "<p>Body <em>em</em>.</p>\n"
            "</details>",
        )

    def test_title_rules_match_bang_and_bang_stays_a_div(self):
        default_title = _render("??? note\n\n    Body.\n")
        self.assertEqual(
            default_title,
            '<details class="admonition note">\n'
            '<summary class="admonition-title">Note</summary>\n'
            "<p>Body.</p>\n"
            "</details>",
        )
        empty_title = _render('??? warning ""\n\n    No title.\n')
        self.assertEqual(
            empty_title,
            '<details class="admonition warning">\n'
            "<p>No title.</p>\n"
            "</details>",
        )
        self.assertNotIn("<summary", empty_title)
        classic = _render('!!! note "Hello"\n\n    Body.\n')
        self.assertEqual(
            classic,
            '<div class="admonition note">\n'
            '<p class="admonition-title">Hello</p>\n'
            "<p>Body.</p>\n"
            "</div>",
        )

    def test_following_indented_block_stays_inside_the_disclosure(self):
        html = _render('??? note "T"\n\n    first\n\n    second\n')
        self.assertEqual(
            html,
            '<details class="admonition note">\n'
            '<summary class="admonition-title">T</summary>\n'
            "<p>first</p>\n"
            "<p>second</p>\n"
            "</details>",
        )

    def test_list_inside_disclosure_and_both_markers_in_one_document(self):
        html = _render(
            '!!! note "Stay"\n\n'
            "    A\n\n"
            '??? tip "Items"\n\n'
            "    * one\n"
            "    * *two*\n"
        )
        self.assertEqual(
            html,
            '<div class="admonition note">\n'
            '<p class="admonition-title">Stay</p>\n'
            "<p>A</p>\n"
            "</div>\n"
            '<details class="admonition tip">\n'
            '<summary class="admonition-title">Items</summary>\n'
            "<ul>\n"
            "<li>one</li>\n"
            "<li><em>two</em></li>\n"
            "</ul>\n"
            "</details>",
        )


if __name__ == "__main__":
    unittest.main()
