# Clickable code

The `clickable_code` plugin links identifiers inside fenced code blocks to their
documentation and adds `[source]` links next to headings whose IDs look like
Python import paths.

- Identifiers in multi-line `<code>` blocks resolve through `mkdocs-autorefs`,
  so the import path must match something in the reference section.
- Absolute links like `/reference/demo_package/` are rewritten relative to the
  current page.
- Set `repo_url` in `mkdocs.yml` (autodetected from `git remote` if omitted) to
  generate source links.

### Demo

```python
from demo_package.math import MovingAverage, scale_values

avg = MovingAverage(window=4)
data = scale_values([1, 2, 3, 4], factor=1.5)
for value in data:
    avg.update(value)
```

<div style="height: 300px"><i>Some padding div to demonstrate what happens when you click on the `MovingAverage` identifier above.</i></div>

#### Redirection for MovingAverage {: #demo_package.math.MovingAverage }

This heading receives a `[source]` link that points at the exact line inside the
demo package on GitHub. Additionally, any occurrence of `MovingAverage` inside code blocks will
link here.

### Code

Add any code block like this to your markdown file:

````md
```python
from demo_package.math import MovingAverage, scale_values

avg = MovingAverage(window=4)
data = scale_values([1, 2, 3, 4], factor=1
for value in data:
    avg.update(value)
```

#### Redirection for MovingAverage {: #demo_package.math.MovingAverage }

This heading receives a `[source]` link that points at the exact line inside the
demo package on GitHub. Additionally, any occurrence of `MovingAverage` inside code blocks will
link here. You can put this anywhere in your docs, not necessarily next to the code block.
````

and enable the `clickable_code` plugin in your `mkdocs.yml`. Set the `repo_url` to
to your project repository to generate source links. To ensure that overrides (like
the `{: #demo_package.math.MovingAverage }` above) are the one that take precedence when
the user clicks on an identifier, set the `priority` option of `autorefs` to have
`reference` after `*`.

```yaml
plugins:
    ...
    - autorefs:
      priority:
        - "*"
        - reference
    - clickable_code
      repo_url: https://github.com/aphp/mkdocs-eds
    ...
```
