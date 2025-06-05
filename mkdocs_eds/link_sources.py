"""
Adapted from
https://github.com/aphp/edsnlp/blob/8e9ed84f56e6af741023e8b3a9de38ba93912953/docs/scripts/plugin.py
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

import jedi
from bs4 import BeautifulSoup
from mkdocs.config import Config
from mkdocs.config import config_options as opt
from mkdocs.plugins import BasePlugin, event_priority


class LinkSourcesPlugin(BasePlugin):
    """
    A MkDocs plugin that adds source links (e.g. GitHub links) to headings in
    the documentation.
    """

    config_scheme = (
        ("repo_url", opt.Type(Optional[str], default=None)),
        ("pattern", opt.Type(Optional[str], default=None)),
    )

    def on_config(self, config: Config) -> Config:
        # Cache the current commit so we don't run the command on every page
        self._commit = os.popen("git rev-parse --short HEAD").read().strip()
        return config

    @event_priority(-2000)  # run after almost everything
    def on_post_page(self, output, page, config):
        soup = BeautifulSoup(output, "html.parser")

        for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            ident = heading.get("id", "")
            if not re.match(self.config["pattern"], ident) or "--" in ident:
                continue

            package = ident.split(".")[1]
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

            url = (
                f"{repo_url.rstrip('/')}/blob/"
                f"{self._commit}/{file_path}#L{inference[0].line}"
            )

            heading.append(
                BeautifulSoup(
                    f'<span class="sourced-heading-spacer"></span>'
                    f'<a href="{url}" target="_blank">[source]</a>',
                    "html.parser",
                )
            )
            heading["class"] = heading.get("class", []) + ["sourced-heading"]

        return str(soup)
