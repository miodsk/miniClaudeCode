from langchain_core.tools import tool
from pathlib import Path
import re


class SkillLoader:
    """技能加载器，从 graph/skills 目录扫描 SKILL.md 文件"""

    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills = {}
        self._load_all()

    def _load_all(self):
        """扫描所有 SKILL.md 文件"""
        if not self.skills_dir.exists():
            return

        for f in sorted(self.skills_dir.rglob("SKILL.md")):
            text = f.read_text(encoding="utf-8")
            meta, body = self._parse_frontmatter(text)
            name = meta.get("name", f.parent.name)
            self.skills[name] = {"meta": meta, "body": body, "path": str(f)}

    def _parse_frontmatter(self, text: str) -> tuple:
        """解析 YAML frontmatter"""
        match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
        if not match:
            return {}, text

        meta = {}
        for line in match.group(1).strip().splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                meta[key.strip()] = val.strip()

        return meta, match.group(2).strip()

    def get_descriptions(self) -> str:
        """Layer 1: 返回技能描述列表，用于 system prompt"""
        if not self.skills:
            return "(无可用技能)"

        lines = []
        for name, skill in self.skills.items():
            desc = skill["meta"].get("description", "无描述")
            lines.append(f"  - {name}: {desc}")
        return "\n".join(lines)

    def get_content(self, name: str) -> str:
        """Layer 2: 返回完整技能内容"""
        skill = self.skills.get(name)
        if not skill:
            available = ", ".join(self.skills.keys()) or "无"
            return f"[错误] 未找到技能 '{name}'。可用技能: {available}"
        return f'<skill name="{name}">\n{skill["body"]}\n</skill>'


# 从 graph/skills 加载技能
SKILLS_DIR = Path(__file__).parent.parent / "skills"
SKILL_LOADER = SkillLoader(SKILLS_DIR)


@tool
def load_skill(name: str) -> str:
    """
    加载技能知识。按需获取特定领域的指导和工作流程。

    Args:
        name: 技能名称，如 "git"、"test"、"code-review"

    Returns:
        技能的完整内容，包含该领域的最佳实践和工作流程
    """
    return SKILL_LOADER.get_content(name)
