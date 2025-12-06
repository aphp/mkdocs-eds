# mkdocs-eds demo

This mini site demonstrates the plugins of mkdocs-eds. Each page in
the **Extensions** section highlights a specific feature with a small snippet
you can copy into your own docs.

## Add mkdocs-eds to your project

Add mkdocs-eds to your Python environment (ideally in a `dev` group):
```bash { data-md-color-scheme="slate" }
uv add git+https://github.com/aphp/mkdocs-eds.git --group dev
```

## Run the demo locally

Clone the project and install it:
```bash { data-md-color-scheme="slate" }
uv sync
```

Build or serve the docs:
```bash { data-md-color-scheme="slate" }
mkdocs serve
```

The demo uses the small package in `demo_package` as input for the
auto-generated reference pages.
