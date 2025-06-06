from pathlib import Path
from typing import Optional

from mkdocs import utils
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.plugins import BasePlugin


class FixFontsPlugin(BasePlugin):
    def on_config(self, config: "MkDocsConfig") -> Optional["MkDocsConfig"]:
        if "override.css" not in config["extra_css"]:
            config["extra_css"].insert(0, "override.css")
        return config

    def on_post_build(self, *, config: "MkDocsConfig") -> None:
        output_base_path = Path(config["site_dir"])
        base_path = Path(__file__).parent.parent / "assets" / "stylesheets"
        from_path = base_path / "override.css"
        to_path = output_base_path / "override.css"
        utils.copy_file(str(from_path), str(to_path))
