# Python-Markdown

A Python implementation of John Gruber's Markdown.

## Install

```bash
pip install -e ".[testing]"
```

## Usage

```python
import markdown
html = markdown.markdown(text)
html = markdown.markdown(text, extensions=["toc"])
```

## Tests

```bash
python -m unittest discover tests
```
