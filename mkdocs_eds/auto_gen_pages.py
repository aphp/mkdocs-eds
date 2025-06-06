"""
Adapted from
https://github.com/aphp/edsnlp/blob/8e9ed84f56e6af741023e8b3a9de38ba93912953/docs/scripts/plugin.py
"""

from __future__ import annotations

from pathlib import Path

from mkdocs.config import Config
from mkdocs.config import config_options as opt
from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import File, Files
from mkdocs.structure.nav import Link, Navigation, Section

REFERENCE_TEMPLATE = """\
# `{ident}`
::: {ident}
    options:
        show_source: false
"""


class AutoGenPagesPlugin(BasePlugin):
    config_scheme = (
        ("package_dirs", opt.Type(list)),
        ("reference_section", opt.Type(str, default="Reference")),
        ("exclude_glob", opt.Type(str, default="assets/fragments/*")),
        ("reference_template", opt.Type(str, default=REFERENCE_TEMPLATE)),
        ("copy_files", opt.Type(dict, default={})),
    )

    def on_config(self, config: Config) -> Config:
        self._package_paths = [Path(p).resolve() for p in self.config["package_dirs"]]
        self._reference_nav: list[dict[str, list | str]] = []
        self._virtual_files: dict[str, str] = {}
        return config

    def on_files(self, files: Files, config: Config) -> Files:
        # Build the virtual files + reference_nav
        self._build_reference()

        # Patch the nav in-place (works because on_files runs before nav is
        # materialized). We replace the simple `"reference": "reference"` key
        # the user might have in `mkdocs.yml` with the detailed nested list
        # produced above.
        for item in config["nav"]:
            print("NAV", item)
            if not isinstance(item, dict):
                continue
            key = next(iter(item))
            if not isinstance(item[key], str):
                continue
            if item[key].strip("/") == "reference":
                item[key] = self._reference_nav

        # Copy files specified in `copy_files` to the virtual files dict.
        for dest, source in self.config["copy_files"].items():
            source_path = Path(source).resolve()
            if not source_path.exists():
                raise ValueError(f"Source file {source} does not exist.")
            # dest is relative to the docs_dir
            self._virtual_files[str(dest.lstrip("/"))] = source_path.read_text()

        # Filter out files that match the exclude_glob pattern
        new_files = [
            f for f in files if not Path(f.src_path).match(self.config["exclude_glob"])
        ] + [
            File(
                path,
                config["docs_dir"],
                config["site_dir"],
                config["use_directory_urls"],
            )
            for path in self._virtual_files
        ]
        return Files(new_files)

    def on_page_read_source(self, page, config: Config):
        return self._virtual_files.get(page.file.src_path)

    def on_nav(self, nav: Navigation, config, files):
        """
        Inject a visible 'Overview' link at the top of each directory.
        The reason for this is that I find unclear in base MkDocs
        that the directory nav link may contain information. Turn this
        into an Overview link is way clearer imo.
        """

        def walk(node):
            if isinstance(node, list):
                for n in node:
                    walk(n)

            elif isinstance(node, Section):
                # We don't want to add Overview links to the reference section
                if node.title == self.config["reference_section"]:
                    return
                # Add Overview-link
                if (
                    node.children
                    and node.children[0].is_page
                    and node.children[0].is_index
                ):
                    first = node.children[0]
                    link = Link(title=first.title, url=first.url)
                    link.is_index = True
                    first.title = "Overview"
                    node.children.insert(0, link)
                walk(node.children)

            elif isinstance(node, Navigation):
                walk(node.items)

        walk(nav.items)
        return nav

    # ------------------------------------------------------------------ helpers
    def _build_reference(self):
        """Populate self._reference_nav and self._virtual_files."""
        for package_root in self._package_paths:
            for py in sorted(package_root.rglob("*.py")):
                module_path = py.relative_to(package_root.parent).with_suffix("")
                doc_path = Path("reference") / py.relative_to(
                    package_root.parent
                ).with_suffix(".md")

                nav_cursor = self._reference_nav
                parts = list(module_path.parts)

                for part in parts[:-1]:
                    child = next((d[part] for d in nav_cursor if part in d), None)
                    if child is None:
                        child = []
                        nav_cursor.append({part: child})
                    nav_cursor = child

                if parts[-1] == "__init__":
                    parts = parts[:-1]
                    doc_path = doc_path.with_name("index.md")
                    nav_cursor.append({"index.md": str(doc_path)})
                elif parts[-1] == "__main__":
                    continue
                else:
                    nav_cursor.append({parts[-1]: str(doc_path)})

                ident = ".".join(parts)
                self._virtual_files[str(doc_path)] = self.config[
                    "reference_template"
                ].format(ident=ident)
