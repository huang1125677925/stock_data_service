import os
import sys
import importlib.util
import logging

logger = logging.getLogger(__name__)

class SkillManager:
    """
    通用 Skill 管理器。
    用于从项目的 skills 目录中动态加载所有技能的指令（SKILL.md）、参考资料（references/*）
    以及工具脚本（scripts/*.py）。
    """
    def __init__(self, skills_dir_name="skill"):
        # 默认技能目录在项目根目录下的 skill 文件夹
        # 优先读 Django settings.BASE_DIR，若 Django 未配置则基于本文件位置推算项目根目录
        try:
            from django.conf import settings
            self.base_dir = str(getattr(settings, 'BASE_DIR', os.path.dirname(os.path.dirname(__file__))))
        except Exception:
            self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.skills_dir = os.path.join(self.base_dir, skills_dir_name)

    def get_all_skills_prompts(self) -> str:
        """
        遍历 skills 目录，将所有技能的 SKILL.md 及其 references 组合成一段完整的提示词。
        """
        if not os.path.exists(self.skills_dir):
            return ""

        skill_prompts = []
        try:
            for skill_name in os.listdir(self.skills_dir):
                skill_path = os.path.join(self.skills_dir, skill_name)
                if os.path.isdir(skill_path):
                    prompt = self._load_single_skill_prompt(skill_path, skill_name)
                    if prompt:
                        skill_prompts.append(prompt)
        except Exception as e:
            logger.error(f"Error loading skills prompts from {self.skills_dir}: {e}")

        if not skill_prompts:
            return ""

        return "\n\n" + "="*20 + " 以下是已注入的系统技能 (Skills) " + "="*20 + "\n\n" + "\n\n---\n\n".join(skill_prompts)

    def _load_single_skill_prompt(self, skill_path: str, skill_name: str) -> str:
        """
        加载单个技能文件夹。
        读取 SKILL.md，并附加 references 目录下的文档内容。
        """
        skill_md_path = os.path.join(skill_path, "SKILL.md")
        if not os.path.exists(skill_md_path):
            return ""

        try:
            with open(skill_md_path, "r", encoding="utf-8") as f:
                skill_content = f.read().strip()
        except Exception as e:
            logger.error(f"Failed to read {skill_md_path}: {e}")
            return ""

        # 加载 references 目录中的所有 markdown 或 text 文件
        references_dir = os.path.join(skill_path, "references")
        refs_content = ""
        if os.path.exists(references_dir) and os.path.isdir(references_dir):
            refs = []
            try:
                for ref_file in os.listdir(references_dir):
                    if ref_file.endswith(".md") or ref_file.endswith(".txt"):
                        ref_path = os.path.join(references_dir, ref_file)
                        with open(ref_path, "r", encoding="utf-8") as rf:
                            refs.append(f"### 参考文档: {ref_file}\n{rf.read().strip()}")
            except Exception as e:
                logger.error(f"Failed to read references for skill {skill_name}: {e}")
            
            if refs:
                refs_content = "\n\n**【技能参考资料/References】**:\n" + "\n\n".join(refs)

        return f"## 技能: {skill_name}\n\n{skill_content}{refs_content}"

    def register_all_skill_tools(self, mcp_server):
        """
        动态加载所有 skill 的 scripts 目录下的 Python 脚本，并调用其 register_tools(mcp) 方法。
        要求：Python 脚本中需定义 `def register_tools(mcp):` 函数。
        """
        if not os.path.exists(self.skills_dir):
            return

        try:
            for skill_name in os.listdir(self.skills_dir):
                skill_path = os.path.join(self.skills_dir, skill_name)
                if os.path.isdir(skill_path):
                    scripts_dir = os.path.join(skill_path, "scripts")
                    if os.path.exists(scripts_dir) and os.path.isdir(scripts_dir):
                        self._register_tools_for_skill(scripts_dir, skill_name, mcp_server)
        except Exception as e:
            logger.error(f"Error registering skill tools from {self.skills_dir}: {e}")

    def _register_tools_for_skill(self, scripts_dir: str, skill_name: str, mcp_server):
        # 确保 scripts 目录在 sys.path 中，以便脚本可以互相引用
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
            
        for file_name in os.listdir(scripts_dir):
            if file_name.endswith(".py") and not file_name.startswith("__"):
                module_name = f"skill_{skill_name}_{file_name[:-3]}"
                file_path = os.path.join(scripts_dir, file_name)
                try:
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        if hasattr(module, "register_tools"):
                            module.register_tools(mcp_server)
                            logger.info(f"Registered tools from skill '{skill_name}' script '{file_name}'")
                except Exception as e:
                    logger.error(f"Failed to load tools from {file_path}: {e}")

skill_manager = SkillManager()
