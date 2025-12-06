# Citations

The `bibtex` plugin understands Pandoc-style citations and builds a references
section for any cited works. Entries come from `docs/references.bib`, and you
can also declare ad-hoc references inside a page.

### Demo

The material theme is used throughout these docs [@mkdocs-material] and Pret is
used for the interactive example [@pret]. Citations can be combined or re-used
multiple times without repeating the bibliography entry.

[@demo-ref]: Wajsburt, 2024. Documentation prototypes with mkdocs-eds.

Need to cite something not in the BibTeX file? Define it inline like
`[@demo-ref]` above and it will show up in the references list.

### Code

For instance in this page:

```md
Some text that cites mkdocs [@mkdocs-material] and mkdocs-eds [@demo-ref].

[@demo-ref]: Wajsburt, 2024. Documentation prototypes with mkdocs-eds.

Some more text.
```

Make sure to enable the `bibtex` plugin in your `mkdocs.yml`:

```yaml
plugins:
    ...
    - bibtex:
        bib_file: references.bib
    ...
```
