import os
import re
import json
from dataclasses import dataclass
from typing import Any


@dataclass
class SkillSpec:
    """
    一个 Skill 的完整运行时描述。
    """
    name: str
    description: str
    tools: list[str]
    prompt: str
    manifest: dict[str, Any]


class SkillRegistry:
    """
    负责从 skills 目录读取：
    - index.md
    - manifest.json
    - skill.md
    """

    def __init__(self, skill_root: str):
        self.skill_root = skill_root

    def load_index(self) -> str:
        """
        读取 skills/index.md。
        这个内容会在 Base Phase 中给模型看，用于选择 skill。
        """
        path = os.path.join(self.skill_root, "index.md")

        if not os.path.exists(path):
            return ""

        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def list_skill_names(self) -> list[str]:
        """
        获取所有 skill 名称。
        """
        if not os.path.exists(self.skill_root):
            return []

        names = []

        for item in os.listdir(self.skill_root):
            skill_dir = os.path.join(self.skill_root, item)
            manifest_path = os.path.join(skill_dir, "manifest.json")

            if os.path.isdir(skill_dir) and os.path.exists(manifest_path):
                names.append(item)

        return names

    def load_skill(self, name: str) -> SkillSpec:
        """
        读取某个 skill：
        - skills/{name}/manifest.json
        - skills/{name}/skill.md
        """
        if not name:
            raise ValueError("Skill name is empty.")

        # 防止路径穿越，例如 ../../etc/passwd
        if not re.match(r"^[a-zA-Z0-9_\-]+$", name):
            raise ValueError(f"Invalid skill name: {name}")

        skill_dir = os.path.join(self.skill_root, name)
        manifest_path = os.path.join(skill_dir, "manifest.json")
        skill_path = os.path.join(skill_dir, "skill.md")

        if not os.path.exists(manifest_path):
            raise FileNotFoundError(f"manifest.json not found for skill: {name}")

        if not os.path.exists(skill_path):
            raise FileNotFoundError(f"skill.md not found for skill: {name}")

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        with open(skill_path, "r", encoding="utf-8") as f:
            prompt = f.read()

        return SkillSpec(
            name=manifest.get("name", name),
            description=manifest.get("description", ""),
            tools=manifest.get("tools", []),
            prompt=prompt,
            manifest=manifest
        )