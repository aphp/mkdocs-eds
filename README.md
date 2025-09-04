# mkdocs-eds

A small collection of MkDocs plugins and Markdown extensions to make technical docs nicer and more interactive:

- Auto‑generate a full API reference from your Python packages
- Make code and headings clickable to their source/reference
- Add simple “cards” layouts in Markdown
- Render interactive Python snippets with Pret
- Add citation support from a BibTeX file
- Fix Material theme font scaling for embedded components


## Installation

Add the package to your project (requires Python ≥ 3.9):

```toml
# pyproject.toml
[project.optional-dependencies]
docs = [
  "mkdocs-eds @ git+https://github.com/aphp/mkdocs-eds.git@main#egg=mkdocs-eds ; python_version>='3.9'",
]
```

Or install directly:

```bash
pip install "mkdocs-eds @ git+https://github.com/aphp/mkdocs-eds.git@main#egg=mkdocs-eds"
```

This package vendors patched forks of `mkdocs-autorefs` and `mkdocstrings-python` to enable a few behaviors used below.


## Quick start (mkdocs.yml)

Below is a compact example showing the main pieces together. See the per‑plugin sections for options and details.

```yaml
site_name: Your Site
theme:
  name: material

plugins:
  - auto_gen_pages:
      package_dirs: ["your_package"]
      reference_section: Reference
  - fix_fonts
  - cards
  - search
  - autorefs:
      # Helps disambiguate duplicate anchors; optional but recommended
      priority:
        - "*"
        - reference
  - clickable_code:
      # repo_url is optional; autodetected from git remote if omitted
      repo_url: https://github.com/you/your-repo
  - mkdocstrings_options_templates
  - mkdocstrings:
      enable_inventory: true
      handlers:
        python:
          options:
            docstring_style: numpy
            docstring_section_style: spacy
            members_order: source
            show_signature: false
            merge_init_into_class: true
  - bibtex:
      bibtex_file: "docs/references.bib"
  - pret_snippet_renderer

nav:
  - Getting Started: index.md
  - Reference: reference/
```


## Plugins and features

### Auto‑generated Reference (`auto_gen_pages`)

Automatically builds a full reference section from one or more Python package roots and wires it into your navigation. For each module, a Markdown page is created virtually (no files written to disk) with a `::: package.module` mkdocstrings directive.

Example:

```markdown
# AnnotatedText {: #pret.ui.metanno.AnnotatedText }

::: pret.ui.metanno.AnnotatedText
    options:
        heading_level: 2
        show_bases: false
        show_source: false
        only_class_level: true

```

- Options:
  - `package_dirs` (list, required): Package roots to scan (e.g. `["your_package"]`).
  - `reference_section` (str, default `Reference`): Title for the “Reference” section in the nav.
  - `exclude_glob` (str, default `assets/fragments/*`): Files to omit from the build.
  - `reference_template` (str): Template used for each generated page.
  - `copy_files` (mapping): Copy arbitrary files into the virtual docs tree, e.g. `{"changelog.md": "changelog.md"}`.
- Nav behavior:
  - If your `nav` contains `Reference: reference/`, it is replaced with a nested tree matching your package layout.
  - Each non‑reference section gets a visible “Overview” link pointing to the index of that section.

Example:

```yaml
plugins:
  - auto_gen_pages:
      package_dirs: ["your_package"]
      reference_section: Reference
      copy_files:
        changelog.md: changelog.md
```


### Clickable Code (`clickable_code`)

Adds two kinds of links to your pages:

- Code → docs: Turns Python identifiers found inside multi‑line `<code>` blocks into links to their mkdocstrings reference pages (resolved via `mkdocs‑autorefs`). You can restrict linking via a regex `pattern` (match against full import path).
- Headings → source: Appends a `[source]` link to object headings (whose IDs look like `package.module.Object`) pointing to the exact line on your repo at the current commit.

It also makes a few quality‑of‑life tweaks:

- Converts absolute links (`href="/..."`) to relative links based on the current page.
- Turns literal component mentions into links by scanning Python entry points:
  - `eds.<component>` links if a matching `spacy_factories` / `edsnlp_factories` entry point exists.
  - Registry literals like `'@group': 'name'` become links when resolvable.

Options:

```yaml
plugins:
  - clickable_code:
      # Optional; autodetected from `git remote get-url origin` if omitted
      repo_url: https://github.com/you/your-repo
      # Optional: only link identifiers matching this regex
      pattern: ^your_package\.
```

Note: This plugin replaces the core `autorefs` plugin instance internally to avoid event ordering issues. Keep `autorefs` enabled in your `plugins` list (optionally with the `priority` setting shown above) so that cross‑references work across your site.


### Cards (`cards`)

Add simple card layouts using a lightweight Markdown block extension and bundled CSS. Start a group of cards with a line that begins with `=== card` and then write normal Markdown; each `=== card` starts a new card in the same group.

Example:

````markdown
=== card

    #### Title

    Some description text.

=== card {: href="/guide/" }

    #### Get Started →

    Clickable card linking to the guide.
````

Options (mapped to the underlying Markdown extension):

```yaml
plugins:
  - cards:
      slugify: null         # custom slugify function name (string) or null
      combine_header_slug: false
      separator: "-"
```

The plugin auto‑adds the extension and copies `cards.css` to the site.


### Pret Snippet Renderer (`pret_snippet_renderer`)

Executes Python code blocks and renders their results using [Pret](https://github.com/percevalw/pret) then injects the required JS/CSS assets into your pages. This is handy to show live, interactive components alongside the code that produced them.

- Usage in Markdown:
  - Execute a code block: add `python` language (default executes).
  - Render the result below the block: add the class `render-with-pret`.
  - Make the code collapsible: also add `code--expandable`.
  - Prevent execution: add `no-exec`.

````markdown
Some markdown text before.

```python { .render-with-pret .code--expandable }
from pret.ui.joy import Button, Typography, Stack

Button("Click me!")
```

Some more markdown text.
````

- Theme requirement: if you override the theme, add `<script pret-head-scripts>` in your `main.html` file.

### Bibliography (`bibtex`)

Adds citation support with automatic bibliography generation from a BibTeX file.

- Configure once:
  ```yaml
  plugins:
    - bibtex:
        bibtex_file: docs/references.bib
        # order: unsorted | occurrence | alphabetical (default: unsorted)
  ```
- Cite in Markdown using Pandoc‑style citations: `[@key]`, `[@key1, @key2]`.
- Optionally define ad‑hoc references anywhere in the page:
  ```markdown
  [@myref]: Author, 2024. Title. Journal.
  ```
- A “References” section is appended to each page listing cited works.


### Mkdocstrings Templates (`mkdocstrings_options_templates`)

Points `mkdocstrings` to the custom templates bundled with this package (under `assets/templates`). These templates:

- Support `docstring_style: numpy` and a `docstring_section_style: spacy` that renders a compact parameter table similar to spaCy’s docs
- Include small tweaks for examples, parameters, and source display

Enable by adding the plugin before `mkdocstrings` and set your handler options as usual (see the Quick start snippet above).


### Fix Material Fonts (`fix_fonts`)

Material for MkDocs sets a base font‑size of 125%. This can cause size mismatches when embedding components that assume a 100% root size. This plugin:

- Prepends an `override.css` that resets the base size to 100% and adjusts related sizes accordingly
- Copies the stylesheet to the site root so it loads early


## Tips

- Keep `Reference: reference/` in your `nav`; `auto_gen_pages` will expand it to a full tree from your `package_dirs`.
- If you get cross‑reference collisions (same dotted path exists on multiple pages), set `autorefs.priority` as shown to prefer non‑reference pages over the auto‑generated reference.
- `clickable_code` falls back to your git remote for `repo_url`. For monorepos or detached builds, set it explicitly.
