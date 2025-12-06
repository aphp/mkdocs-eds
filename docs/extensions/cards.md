# Cards layout

Use the `cards` plugin to drop lightweight card layouts straight into Markdown.
Start a card with `=== card`, then write normal Markdown inside each block. Add
`href` attributes to make the whole card clickable.

#### Demo

=== card

    #### Faster onboarding

    Link out to a single page that collects the must-read guides for newcomers.

=== card {: href="/extensions/clickable-code/" }

    #### Clickable code →

    Code blocks can link back into your reference pages automatically.

=== card {: href="/extensions/pret-snippets/" }

    #### Live snippets

    Render live Pret components side by side with their source.

#### Code

Add this to your markdown file:

```md
=== card

    #### Faster onboarding

    Link out to a single page that collects the must-read guides for newcomers.

=== card {: href="/extensions/clickable-code/" }

    #### Clickable code →

    Code blocks can link back into your reference pages automatically.

=== card {: href="/extensions/pret-snippets/" }

    #### Live snippets

    Render live Pret components side by side with their source.
```

and make sure to enable the `cards` plugin in your `mkdocs.yml`:

```yaml
plugins:
  ...
  - cards
  ...
```
