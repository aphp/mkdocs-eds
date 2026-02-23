from __future__ import annotations

import ast
import json
import re
import subprocess
from pathlib import Path, PurePosixPath

import nbformat
from mkdocs import utils
from mkdocs.config import Config
from mkdocs.config import config_options as opt
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import File, Files

WARNING_PATTERNS = [
    re.compile(r"\b(?:User|Deprecation|Future|Runtime|Syntax|Import|Resource)Warning:"),
    re.compile(r"\bwarnings\.warn\("),
]
TABLE_TAG_RE = re.compile(r"<table\b[^>]*>", flags=re.IGNORECASE)
BUTTON_HTML = """
<div style="clear: both;">
  <a href="{download_url}"
     class="md-button md-button--primary"
     style="float: right; margin: 5px 0 0px;
            background-color: var(--md-primary-fg-color);
            border-color: var(--md-primary-fg-color);
            border-radius: 4px;
            display: inline-flex; align-items: center; gap: 6px; padding: 0 0.5em;">
    <svg xmlns="http://www.w3.org/2000/svg" width="20px" height="20px" viewBox="0 0 24 24" fill="none">
        <path d="M3 15C3 17.8284 3 19.2426 3.87868 20.1213C4.75736 21 6.17157 21 9 21H15C17.8284 21 19.2426 21 20.1213 20.1213C21 19.2426 21 17.8284 21 15" stroke="var(--md-primary-bg-color)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M12 3V16M12 16L16 11.625M12 16L8 11.625" stroke="var(--md-primary-bg-color)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    Download notebook
  </a>
</div>
"""  # noqa: E501


def join_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return "".join(value)


def code_fence(source: str, classes: list[str]) -> str:
    if classes:
        class_expr = " ".join(f".{name}" for name in classes)
        start = f"```python {{ {class_expr} }}"
    else:
        start = "```python"
    return f"{start}\n{source}\n```"


def normalize_repo_url(repo_url: str) -> str:
    normalized = repo_url.rstrip("/")
    if normalized.startswith("git@"):
        host_path = normalized[len("git@") :]
        if ":" in host_path:
            host, path = host_path.split(":", 1)
            normalized = f"https://{host}/{path}"
        else:
            normalized = normalized.replace("git@", "https://", 1)
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    if normalized.startswith("git@"):
        normalized = normalized.replace("git@", "https://", 1)
    return normalized.rstrip("/")


class NotebooksToMarkdownPlugin(BasePlugin):
    """
    Convert notebooks in docs/ to virtual Markdown pages.
    """

    config_scheme = (
        ("include_glob", opt.Type(str, default="**/*.ipynb")),
        ("exclude_glob", opt.Type(str, default="**/.ipynb_checkpoints/*")),
        ("download_notebook_link", opt.Type(bool, default=True)),
    )

    def on_config(self, config: Config) -> Config:
        if "notebook.css" not in config["extra_css"]:
            config["extra_css"].append("notebook.css")
        self._virtual_files: dict[str, str] = {}
        self._download_urls: dict[str, str] = {}
        self._docs_dir = Path(config["docs_dir"]).resolve()
        from_mkdocs = config.get("repo_url")
        if from_mkdocs:
            self._repo_url = normalize_repo_url(str(from_mkdocs))
        else:
            try:
                remote = subprocess.check_output(
                    ["git", "remote", "get-url", "origin"],
                    text=True,
                    stderr=subprocess.STDOUT,
                ).strip()
            except Exception:
                self._repo_url = None
            else:
                self._repo_url = normalize_repo_url(remote) if remote else None

        try:
            output = subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"],
                text=True,
                stderr=subprocess.STDOUT,
            ).strip()
        except Exception:
            self._repo_root = None
        else:
            self._repo_root = Path(output).resolve() if output else None

        try:
            self._commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                text=True,
                stderr=subprocess.STDOUT,
            ).strip()
        except Exception:
            self._commit = "main"

        return config

    def on_files(self, files: Files, config: Config) -> Files:
        self._virtual_files.clear()
        self._download_urls.clear()
        notebook_nav_paths: set[str] = set()
        nav = config.get("nav")
        if nav:
            self.rewrite_nav_notebook_paths(nav, notebook_nav_paths)

        files_by_path = {
            PurePosixPath(file.src_path).as_posix(): file for file in files
        }
        virtual_paths: list[str] = []
        for notebook_path in sorted(notebook_nav_paths):
            source_file = files_by_path.get(notebook_path)
            if source_file is None:
                raise ValueError(
                    f"Notebook referenced in nav was not found in docs: {notebook_path}"
                )
            src_path = PurePosixPath(notebook_path)
            src_posix = src_path.as_posix()
            markdown_path = src_path.with_suffix(".md").as_posix()

            self._virtual_files[markdown_path] = self.render_notebook(
                notebook_path=Path(source_file.abs_src_path),
                src_path=src_posix,
            )
            if self.config["download_notebook_link"] and self._repo_url:
                if self._repo_root is not None:
                    try:
                        resolved_notebook = Path(source_file.abs_src_path).resolve()
                        relative = resolved_notebook.relative_to(
                            self._repo_root
                        ).as_posix()
                    except ValueError:
                        relative = f"{self._docs_dir.name}/{src_posix}"
                else:
                    relative = f"{self._docs_dir.name}/{src_posix}"
                self._download_urls[markdown_path] = (
                    f"{self._repo_url}/blob/{self._commit}/{relative}?raw=1"
                )
            virtual_paths.append(markdown_path)

        virtual_path_set = set(virtual_paths)
        base_files = [
            file
            for file in files
            if PurePosixPath(file.src_path).as_posix() not in virtual_path_set
        ]

        new_files = base_files + [
            File(
                path,
                config["docs_dir"],
                config["site_dir"],
                config["use_directory_urls"],
            )
            for path in virtual_paths
        ]
        return Files(new_files)

    def on_page_read_source(self, page, config: Config):
        return self._virtual_files.get(page.file.src_path)

    def on_page_content(self, html, page, config: Config, files):
        download_url = self._download_urls.get(page.file.src_path)
        if not download_url:
            return html
        return BUTTON_HTML.format(download_url=download_url) + html

    def rewrite_nav_notebook_paths(self, node, notebook_paths: set[str]) -> None:
        if isinstance(node, list):
            for idx, item in enumerate(node):
                if isinstance(item, str):
                    if "://" in item or item.startswith("mailto:"):
                        continue
                    path = PurePosixPath(item.strip("/"))
                    if path.suffix.lower() == ".ipynb":
                        notebook_path = path.as_posix()
                        notebook_paths.add(notebook_path)
                        node[idx] = path.with_suffix(".md").as_posix()
                else:
                    self.rewrite_nav_notebook_paths(item, notebook_paths)
            return

        if isinstance(node, dict):
            for key, value in list(node.items()):
                if isinstance(value, str):
                    if "://" in value or value.startswith("mailto:"):
                        continue
                    path = PurePosixPath(value.strip("/"))
                    if path.suffix.lower() == ".ipynb":
                        notebook_path = path.as_posix()
                        notebook_paths.add(notebook_path)
                        node[key] = path.with_suffix(".md").as_posix()
                else:
                    self.rewrite_nav_notebook_paths(value, notebook_paths)

    def render_output(self, output) -> str:
        output_type = output.get("output_type")

        if output_type == "stream":
            text = join_text(output.get("text")).rstrip()
            if not text:
                return ""
            if output.get("name") == "stderr" and any(
                pattern.search(text) for pattern in WARNING_PATTERNS
            ):
                return ""
            return f"```text {{ .code-output }}\n{text}\n```"

        if output_type == "error":
            traceback_text = "\n".join(output.get("traceback", [])).rstrip()
            if traceback_text:
                return f"```text {{ .code-output }}\n{traceback_text}\n```"
            text = join_text(output.get("text")).rstrip()
            if text:
                return f"```text {{ .code-output }}\n{text}\n```"
            return ""

        if output_type not in {"display_data", "execute_result"}:
            return ""

        data = output.get("data", {})
        if "application/vnd.pret+json" in data:
            return ""
        if "application/vnd.jupyter.widget-view+json" in data:
            return ""

        markdown = join_text(data.get("text/markdown")).rstrip()
        if markdown:
            return TABLE_TAG_RE.sub("<table>", markdown)

        png = join_text(data.get("image/png")).strip()
        if png:
            return f"![output](data:image/png;base64,{png})"

        jpeg = join_text(data.get("image/jpeg")).strip()
        if jpeg:
            return f"![output](data:image/jpeg;base64,{jpeg})"

        html = join_text(data.get("text/html")).rstrip()
        if html:
            return TABLE_TAG_RE.sub("<table>", html)

        plain = join_text(data.get("text/plain")).rstrip()
        if plain:
            return f"```text {{ .code-output }}\n{plain}\n```"

        if "application/json" in data:
            raw_json = data["application/json"]
            if isinstance(raw_json, str):
                payload = raw_json
            else:
                payload = json.dumps(raw_json, indent=2, ensure_ascii=False)
            return f"```json {{ .code-output }}\n{payload}\n```"

        return ""

    def cell_to_markdown(self, cell) -> str:
        cell_type = cell.get("cell_type")
        if cell_type == "markdown":
            return join_text(cell.get("source")).rstrip()

        tags = cell.get("metadata", {}).get("tags", [])
        tag_set = set(tags)
        classes: list[str] = []
        if "render-with-pret" in tag_set or "pret-render" in tag_set:
            classes.append("render-with-pret")
        if "code--expandable" in tag_set:
            classes.append("code--expandable")
        if "no-exec" in tag_set:
            classes.append("no-exec")
        for tag in sorted(tag_set):
            if not tag.startswith("md-class:"):
                continue
            value = tag.split(":", 1)[1].strip()
            if value:
                classes.append(value)

        if cell_type == "raw":
            return code_fence(
                join_text(
                    cell.get("source"),
                ).rstrip(),
                classes=classes,
            )
        if cell_type != "code":
            return ""

        source = join_text(cell.get("source")).rstrip()
        if not source:
            return ""

        has_pret_output = False
        for output in cell.get("outputs", []):
            if output.get("output_type") not in {"display_data", "execute_result"}:
                continue
            data = output.get("data", {})
            if "application/vnd.pret+json" in data:
                has_pret_output = True
                break
            if "application/vnd.jupyter.widget-view+json" in data:
                has_pret_output = True
                break
        if has_pret_output and "render-with-pret" not in classes:
            classes.append("render-with-pret")

        ends_with_expression = False
        tree = None
        try:
            tree = ast.parse(source, mode="exec")
        except SyntaxError:
            pass
        else:
            ends_with_expression = bool(tree.body) and isinstance(
                tree.body[-1], ast.Expr
            )

        if "render-with-pret" in classes and not ends_with_expression:
            try:
                tree = ast.parse(source, mode="exec") if tree is None else tree
            except SyntaxError:
                classes = [name for name in classes if name != "render-with-pret"]
            else:
                last_stmt = tree.body[-1] if tree.body else None
                if (
                    isinstance(last_stmt, ast.Assign)
                    and len(last_stmt.targets) == 1
                    and isinstance(last_stmt.targets[0], ast.Name)
                ):
                    source = f"{source}\n\n{last_stmt.targets[0].id}"
                else:
                    classes = [name for name in classes if name != "render-with-pret"]

        chunks = [code_fence(source, classes)]
        for output in cell.get("outputs", []):
            rendered = self.render_output(output)
            if rendered:
                chunks.append(rendered)
        return "\n\n".join(chunks)

    def render_notebook(self, notebook_path: Path, src_path: str) -> str:
        notebook = nbformat.read(notebook_path, as_version=4)
        chunks: list[str] = []
        for cell in notebook.cells:
            rendered = self.cell_to_markdown(cell)
            if rendered:
                chunks.append(rendered)
        return "\n\n".join(chunks).rstrip() + "\n"

    def on_post_build(self, *, config: "MkDocsConfig") -> None:
        output_base_path = Path(config["site_dir"])
        base_path = Path(__file__).parent / "assets" / "stylesheets"
        from_path = base_path / "notebook.css"
        to_path = output_base_path / "notebook.css"
        utils.copy_file(str(from_path), str(to_path))
