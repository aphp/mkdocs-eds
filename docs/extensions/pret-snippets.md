# Pret snippet renderer

Run Python code blocks and render their results inline using Pret. Add the
`render-with-pret` class to a fenced Python block to execute it at build time
and embed the returned component right below the code. The optional
`code--expandable` class wraps the code in a collapsible `<details>` block.

### Demo

```python { .render-with-pret .code--expandable }
from pret_joy import Button, Typography, Stack

Button("Click me!", sx={"m": 1})
```

### Code

Make sure the `pret` package is installed in your environment before building
the site so the renderer can bundle the assets.

Add this to your markdown file:

````md { title="your-page.md" }
```python { .render-with-pret .code--expandable }
from pret_joy import Button, Typography, Stack

Button("Click me!", sx={"m": 1})
```
````

and enable the `pret_snippet_renderer` plugin in your `mkdocs.yml`:

```yaml { title="mkdocs.yml" }
plugins:
    ...
    - pret_snippet_renderer
    ...
```
