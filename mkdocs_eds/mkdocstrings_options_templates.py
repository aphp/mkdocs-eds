from pathlib import Path
from typing import TYPE_CHECKING, Optional

from mkdocs.plugins import BasePlugin

if TYPE_CHECKING:  # pragma:no cover
    from mkdocs.config.defaults import MkDocsConfig


class MkdocstringsOptionsTemplatesPlugin(BasePlugin):
    def on_config(self, config: "MkDocsConfig") -> Optional["MkDocsConfig"]:
        # Lookup mkdocstrings plugin and change the templates config option
        # to absolute dir to assets/templates/python
        mkdocstrings_plugin = config.plugins.get("mkdocstrings")
        if mkdocstrings_plugin:
            mkdocstrings_plugin.config["custom_templates"] = (
                Path(__file__).parent / "assets/templates"
            )

        return config
