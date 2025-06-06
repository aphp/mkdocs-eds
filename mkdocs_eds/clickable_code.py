from __future__ import annotations

import os
import re
from bisect import bisect_right
from collections import defaultdict
from pathlib import Path
from typing import Tuple

import jedi
import mkdocs.plugins
import mkdocs.structure.pages
import parso
import regex
from bs4 import BeautifulSoup
from mkdocs import utils
from mkdocs.config import Config
from mkdocs.config import config_options as opt
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.plugins import BasePlugin
from mkdocs_autorefs.plugin import AutorefsPlugin

try:
    from importlib.metadata import entry_points
except ImportError:
    from importlib_metadata import entry_points

HREF_REGEX = (
    r"(?<=<\s*(?:a[^>]*href|img[^>]*src)=)"
    r'(?:"([^"]*)"|\'([^\']*)|[ ]*([^ =>]*)(?![a-z]+=))'
)
PIPE_REGEX = r"(?<![a-zA-Z0-9._-])eds[.]([a-zA-Z0-9._-]*)(?![a-zA-Z0-9._-])"

HTML_PIPE_REGEX = r"""(?x)
(?<![a-zA-Z0-9._-])
<span[^>]*>eds<\/span>
<span[^>]*>[.]<\/span>
<span[^>]*>([a-zA-Z0-9._-]*)<\/span>
(?![a-zA-Z0-9._-])
"""

REGISTRY_REGEX = r"""(?x)
(?<![a-zA-Z0-9._-])
<span[^>]*>(?:"|&\#39;|&quot;)@([a-zA-Z0-9._-]*)(?:"|&\#39;|&quot;)<\/span>\s*
<span[^>]*>:<\/span>\s*
<span[^>]*>\s*<\/span>\s*
<span[^>]*>(?:"|&\#39;|&quot;)?([a-zA-Z0-9._-]*)(?:"|&\#39;|&quot;)?<\/span>
(?![a-zA-Z0-9._-])
"""

CITATION_RE = r"(\[@(?:[\w_:-]+)(?: *, *@(?:[\w_:-]+))*\])"


class ClickableCodePlugin(BasePlugin):
    """
    A MkDocs plugin that adds source links (e.g. GitHub links) to headings in
    the documentation.
    """

    config_scheme = (
        ("repo_url", opt.Type(str, default=None)),
        ("pattern", opt.Type(str, default=None)),
    )

    @mkdocs.plugins.event_priority(1000)
    def on_config(self, config: MkDocsConfig):
        for event_name, events in config.plugins.events.items():
            for event in list(events):
                if "autorefs" in str(event):
                    events.remove(event)
        old_plugin = config["plugins"]["autorefs"]
        plugin_config = dict(old_plugin.config)
        plugin = AutorefsPlugin()
        config.plugins["autorefs"] = plugin
        config["plugins"]["autorefs"] = plugin
        plugin.load_config(plugin_config)
        if "clickable-code.css" not in config["extra_css"]:
            config["extra_css"].append("clickable-code.css")
        self._commit = os.popen("git rev-parse --short HEAD").read().strip()
        return config

    def on_post_build(self, *, config: "MkDocsConfig") -> None:
        output_base_path = Path(config["site_dir"])
        base_path = Path(__file__).parent.parent / "assets" / "stylesheets"
        from_path = base_path / "clickable-code.css"
        to_path = output_base_path / "clickable-code.css"
        utils.copy_file(str(from_path), str(to_path))

    @classmethod
    def get_ep_namespace(cls, ep, namespace=None):
        if hasattr(ep, "select"):
            return ep.select(group=namespace) if namespace else list(ep._all)
        else:
            return (
                ep.get(namespace, [])
                if namespace
                else (x for g in ep.values() for x in g)
            )

    @mkdocs.plugins.event_priority(-1000)
    def on_post_page(
        self, output: str, page: mkdocs.structure.pages.Page, config: Config
    ):
        """
        1. Replace absolute paths with path relative to the rendered page
           This must be performed after all other plugins have run.
        2. Replace component names with links to the component reference
        Parameters
        ----------
        output
        page
        config
        Returns
        -------
        """
        autorefs: AutorefsPlugin = config["plugins"]["autorefs"]
        ep = entry_points()
        page_url = os.path.join("/", page.file.url)
        factories_entry_points = {
            ep.name: ep.value
            for ep in (
                *self.get_ep_namespace(ep, "spacy_factories"),
                *self.get_ep_namespace(ep, "edsnlp_factories"),
            )
        }
        all_entry_points = defaultdict(dict)
        for ep in self.get_ep_namespace(ep):
            if ep.group.startswith("edsnlp_") or ep.group.startswith("spacy_"):
                group = ep.group.split("_", 1)[1]
                all_entry_points[group][ep.name] = ep.value

        def replace_factory_component(match):
            full_match = match.group(0)
            name = "eds." + match.group(1)
            ep = factories_entry_points.get(name)
            preceding = output[match.start(0) - 50 : match.start(0)]
            if ep is not None and "DEFAULT:" not in preceding:
                try:
                    url = autorefs.get_item_url(ep.replace(":", "."))[0]
                except KeyError:
                    pass
                else:
                    return f"<a href={url}>{name}</a>"
            return full_match

        def replace_any_registry_component(match):
            full_match = match.group(0)
            group = match.group(1)
            name = match.group(2)
            ep = all_entry_points[group].get(name)
            preceding = output[match.start(0) - 50 : match.start(0)]
            if ep is not None and "DEFAULT:" not in preceding:
                try:
                    url = autorefs.get_item_url(ep.replace(":", "."))[0]
                except KeyError:
                    pass
                else:
                    repl = f'<a href={url} class="clickable-discrete-link">{name}</a>'
                    before = full_match[: match.start(2) - match.start(0)]
                    after = full_match[match.end(2) - match.start(0) :]
                    return before + repl + after
            return full_match

        def replace_link(match):
            relative_url = url = match.group(1) or match.group(2) or match.group(3)
            if url.startswith("/"):
                relative_url = os.path.relpath(url, page_url)
            return f'"{relative_url}"'

        output = regex.sub(PIPE_REGEX, replace_factory_component, output)
        output = regex.sub(HTML_PIPE_REGEX, replace_factory_component, output)
        output = regex.sub(REGISTRY_REGEX, replace_any_registry_component, output)

        all_snippets = ""
        all_offsets = []
        all_nodes = []
        soups = []
        for match in regex.finditer("<code>.*?</code>", output, flags=regex.DOTALL):
            node = match.group(0)
            if "\n" in node:
                soup, snippet, python_offsets, html_nodes = self.convert_html_to_code(
                    node
                )
                size = len(all_snippets)
                all_snippets += snippet + "\n"
                all_offsets.extend([size + i for i in python_offsets])
                all_nodes.extend(html_nodes)
                soups.append((soup, match.start(0), match.end(0)))

        interpreter = jedi.Interpreter(all_snippets, [{}])
        line_lengths = [0]
        for line in all_snippets.split("\n"):
            line_lengths.append(len(line) + line_lengths[-1] + 1)
        line_lengths[-1] -= 1

        for name in self.iter_names(interpreter._module_node):
            try:
                line, col = name.start_pos
                offset = line_lengths[line - 1] + col
                node_idx = bisect_right(all_offsets, offset) - 1
                node = all_nodes[node_idx]
                gotos = interpreter.goto(line, col, follow_imports=True)
                gotos = [
                    goto
                    for goto in gotos
                    if goto
                    and goto.full_name
                    and goto.full_name.startswith("pret")
                    and goto.type != "module"
                ]
                goto = gotos[0] if gotos else None
                if goto:
                    url = autorefs.get_item_url(goto.full_name)[0]
                    if not node.find_parents("a"):
                        node.replace_with(
                            BeautifulSoup(
                                f'<a class="clickable-discrete-link" href="{url}">{node}</a>',  # noqa: E501
                                "html5lib",
                            )
                        )
            except Exception:
                pass

        for soup, start, end in reversed(soups):
            output = output[:start] + str(soup.find("code")) + output[end:]

        output = regex.sub(HREF_REGEX, replace_link, output)

        soup = BeautifulSoup(output, "html.parser")
        for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            ident = heading.get("id", "")
            if (
                self.config["pattern"] and not re.match(self.config["pattern"], ident)
            ) or "--" in ident:
                continue
            if "." not in ident:
                continue
            package = ident.split(".")[0]
            interpreter = jedi.Interpreter(
                f"import {package}; {ident}", namespaces=[{}]
            )
            inference = interpreter.infer(1, len(f"import {package}; {ident}"))
            if not inference:
                continue
            try:
                file_path = inference[0].module_path.relative_to(Path.cwd())
            except Exception:
                continue
            repo_url = self.config["repo_url"]
            if not repo_url:
                try:
                    repo_url = os.popen("git remote get-url origin").read().strip()
                except Exception:
                    raise ValueError(
                        "Please set 'repo_url' in your mkdocs.yml or ensure "
                        "the current directory is a git repository with a "
                        "remote named 'origin'."
                    )
            if repo_url.startswith("git@"):
                repo_url = repo_url.replace("git@", "https://")
            url = f"{repo_url.rstrip('/')}/blob/{self._commit}/{file_path}#L{inference[0].line}"  # noqa: E501
            heading.append(
                BeautifulSoup(
                    f'<span class="sourced-heading-spacer"></span>'
                    f'<a href="{url}" target="_blank">[source]</a>',
                    "html.parser",
                )
            )
            heading["class"] = heading.get("class", []) + ["sourced-heading"]
        return str(soup)

    @classmethod
    def iter_names(cls, root):
        if isinstance(root, parso.python.tree.Name):
            yield root
        for child in getattr(root, "children", ()):
            yield from cls.iter_names(child)

    @classmethod
    def convert_html_to_code(
        cls, html_content: str
    ) -> Tuple[BeautifulSoup, str, list, list]:
        pre_html_content = "<pre>" + html_content + "</pre>"
        soup = list(BeautifulSoup(pre_html_content, "html5lib").children)[0]
        code_element = soup.find("code")
        line_lengths = [0]
        for line in pre_html_content.split("\n"):
            line_lengths.append(len(line) + line_lengths[-1] + 1)
        line_lengths[-1] -= 1
        python_code = ""
        code_offsets = []
        html_nodes = []
        code_offset = 0

        def extract_text_with_offsets(el):
            nonlocal python_code, code_offset
            for content in el.contents:
                if isinstance(content, str):
                    python_code += content
                    code_offsets.append(code_offset)
                    code_offset += len(content)
                    html_nodes.append(content)
                    continue
                if "md-annotation" not in content.get("class", ""):
                    extract_text_with_offsets(content)

        extract_text_with_offsets(code_element)

        return soup, python_code, code_offsets, html_nodes
