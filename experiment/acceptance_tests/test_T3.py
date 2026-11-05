"""Hidden acceptance tests for T3. Do not copy these into either condition."""

import unittest
from html.parser import HTMLParser

import markdown


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = {"tag": "root", "attrs": {}, "children": [], "data": ""}
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = {"tag": tag, "attrs": dict(attrs), "children": [], "data": ""}
        self.stack[-1]["children"].append(node)
        self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        node = {"tag": tag, "attrs": dict(attrs), "children": [], "data": ""}
        self.stack[-1]["children"].append(node)

    def handle_endtag(self, tag):
        if len(self.stack) > 1 and self.stack[-1]["tag"] == tag:
            self.stack.pop()

    def handle_data(self, data):
        self.stack[-1]["data"] += data


def _parse(html):
    builder = _TreeBuilder()
    builder.feed(html)
    return builder.root


def _walk(node):
    yield node
    for child in node["children"]:
        yield from _walk(child)


def _text(node):
    parts = [node["data"]]
    for child in node["children"]:
        parts.append(_text(child))
    return "".join(parts)


def _has(attrs, name):
    return name in attrs


def _checkbox_ok(node, checked):
    attrs = node["attrs"]
    if node["tag"] != "input":
        return False
    if attrs.get("type") != "checkbox":
        return False
    if not _has(attrs, "disabled"):
        return False
    return _has(attrs, "checked") == checked


def _task_items(html):
    items = []
    for node in _walk(_parse(html)):
        if node["tag"] != "li":
            continue
        host = node
        if node["children"] and node["children"][0]["tag"] == "p":
            host = node["children"][0]
        checkbox = next((child for child in host["children"] if child["tag"] == "input"), None)
        items.append((node, checkbox, " ".join(_text(node).split())))
    return items


class TaskListExtension(unittest.TestCase):
    def test_tight_lists_load_by_short_name_and_dotted_path(self):
        source = "- [ ] todo\n- [x] done\n- [X] also\n"
        for extension in ("tasklist", "markdown.extensions.tasklist"):
            html = markdown.markdown(source, extensions=[extension])
            items = _task_items(html)
            self.assertEqual(len(items), 3)
            self.assertTrue(all("task-list-item" in (li["attrs"].get("class") or "") for li, _, _ in items))
            self.assertTrue(_checkbox_ok(items[0][1], checked=False))
            self.assertTrue(_checkbox_ok(items[1][1], checked=True))
            self.assertTrue(_checkbox_ok(items[2][1], checked=True))
            self.assertEqual([text for _, _, text in items], ["todo", "done", "also"])
            self.assertNotIn("[ ]", html)
            self.assertNotIn("[x]", html)
            self.assertNotIn("[X]", html)

        ordered = markdown.markdown(
            "1. [ ] first\n2. [X] second\n",
            extensions=["markdown.extensions.tasklist"],
        )
        items = _task_items(ordered)
        self.assertEqual([text for _, _, text in items], ["first", "second"])
        self.assertFalse(_has(items[0][1]["attrs"], "checked"))
        self.assertTrue(_has(items[1][1]["attrs"], "checked"))

    def test_loose_nested_lists_keep_inline_markdown(self):
        html = markdown.markdown(
            "- [ ] item\n\n    more *yes*\n\n    - [ ] child\n",
            extensions=["markdown.extensions.tasklist"],
        )
        items = _task_items(html)
        self.assertEqual(len(items), 2)
        outer_li, outer_box, outer_text = items[0]
        self.assertEqual(outer_li["children"][0]["tag"], "p")
        self.assertIs(outer_li["children"][0]["children"][0], outer_box)
        self.assertIn("item", outer_text)
        self.assertIn("more yes", outer_text)
        self.assertIn("<em>yes</em>", html)
        self.assertEqual(items[1][2], "child")
        self.assertTrue(_checkbox_ok(items[1][1], checked=False))

    def test_non_task_text_is_unchanged(self):
        source = "See [x] in prose.\n\n- not a task\n- [x]no-space\n"
        with_extension = markdown.markdown(source, extensions=["markdown.extensions.tasklist"])
        without = markdown.markdown(source)
        self.assertEqual(with_extension, without)
        self.assertNotIn("<input", with_extension)

    def test_item_class_and_both_output_formats(self):
        source = "- [x] done\n"
        from markdown.extensions.tasklist import TaskListExtension as ExtensionClass

        via_keyword = markdown.markdown(
            source,
            extensions=[ExtensionClass(item_class="mine")],
            output_format="html",
        )
        via_config = markdown.markdown(
            source,
            extensions=["markdown.extensions.tasklist"],
            extension_configs={"markdown.extensions.tasklist": {"item_class": "mine"}},
            output_format="html",
        )
        for html in (via_keyword, via_config):
            self.assertNotIn("/>", html)
            items = _task_items(html)
            self.assertEqual(len(items), 1)
            self.assertIn("mine", items[0][0]["attrs"].get("class", ""))
            self.assertNotIn("task-list-item", items[0][0]["attrs"].get("class", ""))
            self.assertTrue(_checkbox_ok(items[0][1], checked=True))
            self.assertEqual(items[0][2], "done")

        xhtml = markdown.markdown(
            source,
            extensions=["markdown.extensions.tasklist"],
            output_format="xhtml",
        )
        self.assertIn("/>", xhtml)
        self.assertTrue(_checkbox_ok(_task_items(xhtml)[0][1], checked=True))


if __name__ == "__main__":
    unittest.main()
