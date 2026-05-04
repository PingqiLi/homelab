import json
import logging
from typing import Any, Optional

from openai import AzureOpenAI, OpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Episode(BaseModel):
    title_en: Optional[str] = None
    title_zh: Optional[str] = None
    title_jp: Optional[str] = None
    season: int = 1
    season_raw: str = ""
    episode: int = 0
    sub: str = ""
    group: str = ""
    resolution: str = ""
    source: str = ""


DEFAULT_PROMPT = """\
你是一个专门解析动漫种子文件名的助手，请从文件名中提取结构化信息并以 JSON 格式返回。

常见格式举例：
- [字幕组] 中文名 / English Title - 01 [1080p][WebRip][简繁内封字幕]
- [Group] Show Name S01E12 [720p][HEVC][CHS&CHT]
- [字幕组] 番剧名 第01话 [BDRip 1080p HEVC AAC]

字段提取规则：
- group: 文件名开头方括号内的字幕组名，如 "LoliHouse"、"喵萌奶茶屋&LoliHouse"、"ANi"
- title_zh: 中文番剧名（汉字组成的主标题，忽略括号内「检索用」提示词）
- title_en: 英文番剧名（通常在斜线 / 后面，或全英文文件名中的主标题）
- title_jp: 日文番剧名（含假名的标题，若与中文相同则留 null）
- season: 季数整数，S01→1，第一季→1，无标识默认为 1
- season_raw: 季数原始字符串，如 "S01"、"第一季"，无则空字符串
- episode: 集数整数，"- 01"→1，"E12"→12，"第03话"→3；v2/v3 是版本号不是集数，忽略
- sub: 字幕语言，如 "简中"、"繁中"、"简繁内封"、"CHS"、"CHT"
- resolution: 分辨率，如 "1080p"、"720p"、"4K"
- source: 视频来源，如 "WebRip"、"BDRip"、"WEB-DL"、"Blu-ray"

注意：
- season 和 episode 必须是整数（number 类型），不能是字符串
- 无法确定的字段留 null 或空字符串，绝不捏造信息
- 括号内「检索用：xxx」不是标题的一部分，忽略
"""


class OpenAIParser:
    def __init__(
        self,
        api_key: str,
        api_base: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        api_type: str = "openai",
        **kwargs,
    ) -> None:
        if not api_key:
            raise ValueError("API key is required.")
        if api_type == "azure":
            self.client = AzureOpenAI(
                api_key=api_key,
                base_url=api_base,
                azure_deployment=kwargs.get("deployment_id", ""),
                api_version=kwargs.get("api_version", "2023-05-15"),
            )
        else:
            self.client = OpenAI(api_key=api_key, base_url=api_base)

        self.model = model
        self.openai_kwargs = kwargs

    def parse(
        self, text: str, prompt: str | None = None, asdict: bool = True
    ) -> dict | str:
        if not prompt:
            prompt = DEFAULT_PROMPT

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text},
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )
            result_str = resp.choices[0].message.content
            result = json.loads(result_str)
        except Exception as e:
            logger.warning(f"[OpenAI] parse failed for '{text}': {e}")
            return {} if asdict else ""

        # Coerce season/episode to int in case the LLM returns strings
        for field, default in (("season", 1), ("episode", 0)):
            val = result.get(field)
            if val is None or val == "":
                result[field] = default
            elif not isinstance(val, int):
                try:
                    result[field] = int(val)
                except (ValueError, TypeError):
                    result[field] = default

        logger.debug("[OpenAI] parsed '%s' → %s", text, result)
        return result if asdict else json.dumps(result, ensure_ascii=False)
