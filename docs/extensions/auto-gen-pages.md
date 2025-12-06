# Auto-generated reference

The `auto_gen_pages` plugin scans one or more package roots and creates virtual
Markdown pages for every module it finds. The generated pages are routed into
your navigation so you never have to maintain a manual reference section.

Key behaviors in this demo:

- The `Reference: reference/` entry in `mkdocs.yml` is replaced with a nested
  tree that mirrors the `demo_package` layout.
- Each module gets a `::: demo_package.module` directive using the custom
  mkdocstrings templates shipped with mkdocs-eds.
- Section index pages gain a visible **Overview** link so the directory itself
  is clearly clickable.

```yaml
plugins:
  - auto_gen_pages:
      package_dirs:
        - demo_package
      reference_section: Reference
```

Add or remove modules under `demo_package` and the reference updates
automatically on the next build.
