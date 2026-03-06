"""Runtime settings – DB-backed overrides on top of pydantic Settings."""
from __future__ import annotations

import os
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path

from ..core.config import get_settings
from ..db.session import SessionLocal
from ..models import AppSetting

_BOOL_TRUE = {"1", "true", "yes", "on"}

# Default prompts
DEFAULT_NOTICE_SYSTEM_PROMPT = "你是学习小组内容编辑助手，要求输出准确、紧凑、可读。"
DEFAULT_NOTICE_BLOG_TASK = (
    "把输入记录整理成一篇中文博客 HTML，输出必须是纯 HTML（不要 markdown 代码块）。"
    "结构包含：标题、导语、按主题分节的小标题、结语。"
    "保留关键事实和时间线，语言自然可读，避免空泛。"
)
DEFAULT_NOTICE_PODCAST_TASK = (
    "把输入记录整理成一份中文播客脚本，时长 3-6 分钟。"
    "需要有开场、主体、结尾，重点清晰，可直接用于语音合成。"
)
DEFAULT_NOTICE_POSTER_TASK = "把输入记录提炼成一份中文海报文案，包含标题、3-6 个重点、结语。"
DEFAULT_POSTER_SYSTEM_PROMPT = (
    "你是海报视觉总监。请把学习记录提炼成可直接用于图像模型作图的中文提示词。"
    "提示词必须聚焦画面本身，避免写成方案说明或长文案。"
)
DEFAULT_POSTER_USER_TEMPLATE = (
    '请基于记录输出一段 120-220 字中文提示词，用于生成"图像感强"的学习小组海报。\n'
    "要求：\n"
    "1) 明确主体、场景、构图、色彩、光影、材质与情绪；\n"
    "2) 画面文字极少，仅允许 0-2 行短标题（每行不超过 12 字）；\n"
    "3) 禁止“主题/排版/颜色/风格/元素：”这类栏目写法；\n"
    "4) 不要解释，不要分点，不要 markdown，只输出提示词正文。\n\n"
    "记录输入：\n{records_text}"
)
DEFAULT_VECTOR_CHAT_SYSTEM_PROMPT = (
    "你是 Benoss 本地知识库助手。"
    "只基于给定检索结果回答，不确定就明确说明证据不足。"
    "回答时尽量简洁，并优先给出结论。"
)

_SETTINGS = get_settings()

# Setting definitions (used by admin panel)
SETTING_DEFINITIONS: list[dict] = [
    {
        "key": "BOARD_DEFAULT_DAYS",
        "label": "Board 默认天数",
        "type": "int",
        "group": "站点",
        "description": "Board 页默认展示最近多少天。",
        "min": 1,
        "max": 30,
        "default": 7,
    },
    {
        "key": "BOARD_TOP_TAGS_DAYS",
        "label": "Board 热门标签统计天数（0=历史全部）",
        "type": "int",
        "group": "站点",
        "description": "热门标签统计窗口；0=从最早记录。",
        "min": 0,
        "max": 36500,
        "default": 0,
    },
    {
        "key": "BOARD_TOP_TAGS_LIMIT",
        "label": "Board 热门标签 TopN",
        "type": "int",
        "group": "站点",
        "description": "热门标签最多展示多少个。",
        "min": 1,
        "max": 100,
        "default": 10,
    },
    {
        "key": "DIGEST_TIMEZONE",
        "label": "Digest 时区",
        "type": "string",
        "group": "站点",
        "description": "日报任务时区，例如 Asia/Shanghai。",
        "default": "Asia/Shanghai",
    },
    {
        "key": "HOME_AUTO_BUILD_DAILY_ASSETS",
        "label": "自动触发日报生成",
        "type": "bool",
        "group": "站点",
        "description": "首页加载时自动生成昨日日报。",
        "default": True,
    },
    {
        "key": "HOME_DIGEST_RETRY_MINUTES",
        "label": "日报生成重试间隔（分钟）",
        "type": "int",
        "group": "站点",
        "description": "两次自动生成尝试的最短间隔。",
        "min": 1,
        "max": 1440,
        "default": 30,
    },
    {
        "key": "ARCHIVE_RETENTION_DAYS",
        "label": "归档保留天数（0=永久）",
        "type": "int",
        "group": "归档",
        "description": "本地 JSON 归档保留最近多少天；0 表示永久保留。",
        "min": 0,
        "max": 3650,
        "default": 7,
    },
    {
        "key": "ARCHIVE_STORE_FILE_BLOB",
        "label": "归档写入文件正文",
        "type": "bool",
        "group": "归档",
        "description": "是否把文件可解析正文写入归档 JSON。",
        "default": True,
    },
    {
        "key": "LOCAL_DAILY_ARCHIVE_DIR",
        "label": "归档目录",
        "type": "string",
        "group": "归档",
        "description": "每日归档目录路径。",
        "default": str(_SETTINGS.LOCAL_DAILY_ARCHIVE_DIR),
    },
    {
        "key": "AI_ARCHIVE_MULTIMODAL_PARSE",
        "label": "归档多模态解析",
        "type": "bool",
        "group": "归档",
        "description": "解析图片/音频/视频的文本信息后再写入归档。",
        "default": True,
    },
    {
        "key": "AI_ARCHIVE_PARSE_MAX_CHARS",
        "label": "归档解析最大字符数",
        "type": "int",
        "group": "归档",
        "description": "单文件最大解析文本字符数。",
        "min": 600,
        "max": 20000,
        "default": 8000,
    },
    {
        "key": "AI_ARCHIVE_PARSE_TIMEOUT_SECONDS",
        "label": "归档解析超时（秒）",
        "type": "int",
        "group": "归档",
        "description": "单文件多模态解析超时时间。",
        "min": 10,
        "max": 1800,
        "default": 90,
    },
    {
        "key": "AI_NOTICE_FILE_READ_MAX_BYTES",
        "label": "公告读取文件上限（字节）",
        "type": "int",
        "group": "归档",
        "description": "公告生成时单文件最大读取字节数。",
        "min": 65536,
        "max": 8 * 1024 * 1024,
        "default": 524288,
    },
    {
        "key": "AI_NOTICE_IMAGE_URL_EXPIRES_SECONDS",
        "label": "公告图片 URL 过期时间（秒）",
        "type": "int",
        "group": "归档",
        "description": "公告生成使用的签名图片 URL 过期时长。",
        "min": 300,
        "max": 86400,
        "default": 1800,
    },
    {
        "key": "VECTOR_AUTO_REBUILD",
        "label": "向量索引自动重建",
        "type": "bool",
        "group": "向量搜索",
        "description": "归档完成后自动重建向量索引。",
        "default": True,
    },
    {
        "key": "VECTOR_TOP_K",
        "label": "向量搜索 Top-K",
        "type": "int",
        "group": "向量搜索",
        "description": "搜索返回最多多少个结果。",
        "min": 1,
        "max": 50,
        "default": 6,
    },
    {
        "key": "VECTOR_MAX_DOCS",
        "label": "向量索引最大文档数",
        "type": "int",
        "group": "向量搜索",
        "description": "本地向量索引最多存储多少条。",
        "min": 100,
        "max": 100000,
        "default": 4000,
    },
    {
        "key": "VECTOR_EMBEDDING_BATCH_SIZE",
        "label": "向量嵌入批大小",
        "type": "int",
        "group": "向量搜索",
        "description": "重建索引时每批提交 embedding 的文档数。",
        "min": 1,
        "max": 128,
        "default": 16,
    },
    {
        "key": "VECTOR_EMBEDDING_MAX_INPUT_CHARS",
        "label": "向量嵌入输入上限",
        "type": "int",
        "group": "向量搜索",
        "description": "单段文本传给 embedding 模型的最大字符数。",
        "min": 200,
        "max": 20000,
        "default": 4000,
    },
    {
        "key": "LOCAL_VECTOR_STORE_DIR",
        "label": "向量索引目录",
        "type": "string",
        "group": "向量搜索",
        "description": "向量数据库本地存储路径。",
        "default": str(_SETTINGS.LOCAL_VECTOR_STORE_DIR),
    },
    {
        "key": "AI_CHAT_PROVIDER",
        "label": "聊天 AI 服务商",
        "type": "choice",
        "group": "AI 服务",
        "description": "用于公告/日报生成的聊天服务商。",
        "choices": ["openai", "chatanywhere", "deepseek", "aliyun", ""],
        "default": "",
    },
    {
        "key": "AI_EMBEDDING_PROVIDER",
        "label": "Embedding 服务商",
        "type": "choice",
        "group": "AI 服务",
        "description": "向量嵌入使用的服务商。",
        "choices": ["openai", "chatanywhere", "aliyun", ""],
        "default": "",
    },
    {
        "key": "AI_TTS_PROVIDER",
        "label": "TTS 服务商",
        "type": "choice",
        "group": "AI 服务",
        "description": "语音合成使用的服务商。",
        "choices": ["openai", "chatanywhere", "aliyun", ""],
        "default": "",
    },
    {
        "key": "AI_IMAGE_PROVIDER",
        "label": "图像生成服务商",
        "type": "choice",
        "group": "AI 服务",
        "description": "海报图像生成使用的服务商。",
        "choices": ["openai", "chatanywhere", "aliyun", ""],
        "default": "",
    },
    {
        "key": "AI_REQUEST_TIMEOUT_SECONDS",
        "label": "AI 请求超时（秒）",
        "type": "int",
        "group": "AI 服务",
        "description": "调用模型接口的请求超时时间。",
        "min": 5,
        "max": 600,
        "default": 45,
    },
    {
        "key": "AI_MAX_NOTICE_RECORDS",
        "label": "公告最大记录数",
        "type": "int",
        "group": "AI 服务",
        "description": "一次公告生成最多读取多少条记录。",
        "min": 10,
        "max": 1000,
        "default": 180,
    },
    {
        "key": "AI_NOTICE_CONTEXT_MAX_CHARS",
        "label": "公告上下文最大字符数",
        "type": "int",
        "group": "AI 服务",
        "description": "公告拼接上下文总字符上限。",
        "min": 2000,
        "max": 200000,
        "default": 60000,
    },
    {
        "key": "AI_NOTICE_RECORD_MAX_CHARS",
        "label": "单条记录最大字符数",
        "type": "int",
        "group": "AI 服务",
        "description": "公告中单条记录可贡献的最大字符数。",
        "min": 200,
        "max": 20000,
        "default": 3200,
    },
    {
        "key": "AI_NOTICE_ATTACH_IMAGES",
        "label": "公告附带图片上下文",
        "type": "bool",
        "group": "AI 服务",
        "description": "公告生成时是否附带图片 URL 作为上下文。",
        "default": True,
    },
    {
        "key": "AI_NOTICE_MAX_IMAGE_ATTACHMENTS",
        "label": "公告最多附图数量",
        "type": "int",
        "group": "AI 服务",
        "description": "每次公告生成最多附带几张图片。",
        "min": 0,
        "max": 30,
        "default": 6,
    },
    {
        "key": "AI_TTS_VOICE",
        "label": "TTS 默认音色",
        "type": "string",
        "group": "AI 服务",
        "description": "播客语音合成默认 voice。",
        "default": "alloy",
    },
    {
        "key": "AI_TTS_RESPONSE_FORMAT",
        "label": "TTS 输出格式",
        "type": "choice",
        "group": "AI 服务",
        "description": "语音合成输出格式。",
        "choices": ["mp3", "wav", "opus", "flac", "pcm", "aac"],
        "default": "mp3",
    },
    {
        "key": "AI_TTS_MAX_INPUT_CHARS",
        "label": "TTS 输入上限",
        "type": "int",
        "group": "AI 服务",
        "description": "语音合成单次输入最大字符数。",
        "min": 100,
        "max": 20000,
        "default": 3600,
    },
    {
        "key": "AI_TTS_FALLBACK_LOCAL",
        "label": "TTS 失败本地兜底",
        "type": "bool",
        "group": "AI 服务",
        "description": "云 TTS 失败时使用本地兜底音频。",
        "default": True,
    },
    {
        "key": "AI_IMAGE_FALLBACK_LOCAL",
        "label": "图像失败本地兜底",
        "type": "bool",
        "group": "AI 服务",
        "description": "云图像生成失败时使用本地兜底图片。",
        "default": True,
    },
    {
        "key": "NOTICE_SYSTEM_PROMPT",
        "label": "日报 System Prompt",
        "type": "text",
        "group": "AI 提示词",
        "description": "日报生成使用的系统提示词。",
        "default": DEFAULT_NOTICE_SYSTEM_PROMPT,
    },
    {
        "key": "NOTICE_BLOG_TASK",
        "label": "博客生成任务提示",
        "type": "text",
        "group": "AI 提示词",
        "description": "生成博客 HTML 的任务提示。",
        "default": DEFAULT_NOTICE_BLOG_TASK,
    },
    {
        "key": "NOTICE_PODCAST_TASK",
        "label": "播客脚本任务提示",
        "type": "text",
        "group": "AI 提示词",
        "description": "生成播客脚本的任务提示。",
        "default": DEFAULT_NOTICE_PODCAST_TASK,
    },
    {
        "key": "NOTICE_POSTER_TASK",
        "label": "海报文案任务提示",
        "type": "text",
        "group": "AI 提示词",
        "description": "生成海报文案的任务提示。",
        "default": DEFAULT_NOTICE_POSTER_TASK,
    },
    {
        "key": "POSTER_SYSTEM_PROMPT",
        "label": "海报 System Prompt",
        "type": "text",
        "group": "AI 提示词",
        "description": "海报提示词生成的系统提示词。",
        "default": DEFAULT_POSTER_SYSTEM_PROMPT,
    },
    {
        "key": "POSTER_USER_TEMPLATE",
        "label": "海报 User Template",
        "type": "text",
        "group": "AI 提示词",
        "description": "用于拼装海报提示词的用户模板。",
        "default": DEFAULT_POSTER_USER_TEMPLATE,
    },
    {
        "key": "PODCAST_DEFAULT_STYLE",
        "label": "播客默认风格",
        "type": "choice",
        "group": "AI 提示词",
        "description": "dialogue/speech/interview/news。",
        "choices": ["dialogue", "speech", "interview", "news"],
        "default": "dialogue",
    },
    {
        "key": "VECTOR_CHAT_SYSTEM_PROMPT",
        "label": "向量问答 System Prompt",
        "type": "text",
        "group": "AI 提示词",
        "description": "RAG 问答系统提示词。",
        "default": DEFAULT_VECTOR_CHAT_SYSTEM_PROMPT,
    },
    {
        "key": "OPENAI_API_KEY",
        "label": "OpenAI API Key",
        "type": "string",
        "group": "OpenAI",
        "description": "OpenAI 访问密钥。",
        "default": "",
        "secret": True,
    },
    {
        "key": "OPENAI_API_BASE_URL",
        "label": "OpenAI Base URL",
        "type": "string",
        "group": "OpenAI",
        "description": "OpenAI API 基础地址。",
        "default": "https://api.openai.com/v1",
    },
    {"key": "OPENAI_CHAT_MODEL", "label": "OpenAI Chat Model", "type": "string", "group": "OpenAI", "description": "聊天模型。", "default": "gpt-4o-mini"},
    {"key": "OPENAI_EMBEDDING_MODEL", "label": "OpenAI Embedding Model", "type": "string", "group": "OpenAI", "description": "向量模型。", "default": "text-embedding-3-small"},
    {"key": "OPENAI_TTS_MODEL", "label": "OpenAI TTS Model", "type": "string", "group": "OpenAI", "description": "语音模型。", "default": "gpt-4o-mini-tts"},
    {"key": "OPENAI_IMAGE_MODEL", "label": "OpenAI Image Model", "type": "string", "group": "OpenAI", "description": "图像模型。", "default": "gpt-image-1"},
    {"key": "OPENAI_TRANSCRIBE_MODEL", "label": "OpenAI Transcribe Model", "type": "string", "group": "OpenAI", "description": "语音识别模型。", "default": "whisper-1"},
    {
        "key": "CHAT_ANYWHERE_API_KEY",
        "label": "ChatAnywhere API Key",
        "type": "string",
        "group": "ChatAnywhere",
        "description": "ChatAnywhere 访问密钥。",
        "default": "",
        "secret": True,
    },
    {
        "key": "CHAT_ANYWHERE_API_BASE_URL",
        "label": "ChatAnywhere Base URL",
        "type": "string",
        "group": "ChatAnywhere",
        "description": "ChatAnywhere API 基础地址。",
        "default": "https://api.chatanywhere.tech/v1",
    },
    {
        "key": "CHAT_ANYWHERE_CHAT_MODEL",
        "label": "ChatAnywhere Chat Model",
        "type": "string",
        "group": "ChatAnywhere",
        "description": "聊天模型。",
        "default": "gpt-4o-mini",
    },
    {
        "key": "CHAT_ANYWHERE_EMBEDDING_MODEL",
        "label": "ChatAnywhere Embedding Model",
        "type": "string",
        "group": "ChatAnywhere",
        "description": "向量模型。",
        "default": "text-embedding-3-small",
    },
    {
        "key": "CHAT_ANYWHERE_TTS_MODEL",
        "label": "ChatAnywhere TTS Model",
        "type": "string",
        "group": "ChatAnywhere",
        "description": "语音模型。",
        "default": "gpt-4o-mini-tts",
    },
    {
        "key": "CHAT_ANYWHERE_IMAGE_MODEL",
        "label": "ChatAnywhere Image Model",
        "type": "string",
        "group": "ChatAnywhere",
        "description": "图像模型。",
        "default": "gpt-image-1",
    },
    {
        "key": "CHAT_ANYWHERE_TRANSCRIBE_MODEL",
        "label": "ChatAnywhere Transcribe Model",
        "type": "string",
        "group": "ChatAnywhere",
        "description": "语音识别模型。",
        "default": "whisper-1",
    },
    {
        "key": "DEEPSEEK_API_KEY",
        "label": "DeepSeek API Key",
        "type": "string",
        "group": "DeepSeek",
        "description": "DeepSeek 访问密钥。",
        "default": "",
        "secret": True,
    },
    {
        "key": "DEEPSEEK_API_BASE_URL",
        "label": "DeepSeek Base URL",
        "type": "string",
        "group": "DeepSeek",
        "description": "DeepSeek API 基础地址。",
        "default": "https://api.deepseek.com/v1",
    },
    {"key": "DEEPSEEK_CHAT_MODEL", "label": "DeepSeek Chat Model", "type": "string", "group": "DeepSeek", "description": "聊天模型。", "default": "deepseek-chat"},
    {"key": "DEEPSEEK_EMBEDDING_MODEL", "label": "DeepSeek Embedding Model", "type": "string", "group": "DeepSeek", "description": "向量模型。", "default": "unsupported"},
    {"key": "DEEPSEEK_TTS_MODEL", "label": "DeepSeek TTS Model", "type": "string", "group": "DeepSeek", "description": "语音模型。", "default": "unsupported"},
    {"key": "DEEPSEEK_IMAGE_MODEL", "label": "DeepSeek Image Model", "type": "string", "group": "DeepSeek", "description": "图像模型。", "default": "unsupported"},
    {"key": "DEEPSEEK_TRANSCRIBE_MODEL", "label": "DeepSeek Transcribe Model", "type": "string", "group": "DeepSeek", "description": "语音识别模型。", "default": "unsupported"},
    {
        "key": "ALIYUN_AI_API_KEY",
        "label": "阿里云 AI API Key",
        "type": "string",
        "group": "阿里云 AI",
        "description": "阿里云 DashScope 访问密钥。",
        "default": "",
        "secret": True,
    },
    {
        "key": "ALIYUN_AI_API_BASE_URL",
        "label": "阿里云 AI Base URL",
        "type": "string",
        "group": "阿里云 AI",
        "description": "阿里云兼容 API 基础地址。",
        "default": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    },
    {"key": "ALIYUN_AI_CHAT_MODEL", "label": "阿里云 Chat Model", "type": "string", "group": "阿里云 AI", "description": "聊天模型。", "default": "qwen-plus"},
    {"key": "ALIYUN_AI_EMBEDDING_MODEL", "label": "阿里云 Embedding Model", "type": "string", "group": "阿里云 AI", "description": "向量模型。", "default": "text-embedding-v3"},
    {"key": "ALIYUN_AI_TTS_MODEL", "label": "阿里云 TTS Model", "type": "string", "group": "阿里云 AI", "description": "语音模型。", "default": "qwen3-tts-instruct-flash"},
    {"key": "ALIYUN_AI_IMAGE_MODEL", "label": "阿里云 Image Model", "type": "string", "group": "阿里云 AI", "description": "图像模型。", "default": "qwen-image-max"},
    {"key": "ALIYUN_AI_TRANSCRIBE_MODEL", "label": "阿里云 Transcribe Model", "type": "string", "group": "阿里云 AI", "description": "语音识别模型。", "default": "whisper-1"},
]


def _default_to_str(value: object) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if value is None:
        return ""
    return str(value)


_SETTING_DEFAULTS: dict[str, str] = {}
for _defn in SETTING_DEFINITIONS:
    _SETTING_DEFAULTS[_defn["key"]] = _default_to_str(_defn.get("default"))


def _db_get(key: str) -> str | None:
    with SessionLocal() as db:
        row = db.query(AppSetting).filter(AppSetting.key == key).first()
        return row.value if row else None


@lru_cache(maxsize=1)
def _env_file_values() -> dict[str, str]:
    path = Path(get_settings().REPO_ROOT) / ".env"
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError:
        return {}

    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        env_key = key.strip().upper()
        if not env_key:
            continue
        env_value = value.strip()
        if len(env_value) >= 2 and env_value[0] == env_value[-1] and env_value[0] in {'"', "'"}:
            env_value = env_value[1:-1]
        values[env_key] = env_value
    return values


def _settings_default_value(key: str) -> str | None:
    attr_name = key.upper()
    settings = get_settings()
    if not hasattr(settings, attr_name):
        return None
    return _default_to_str(getattr(settings, attr_name))


def _config_get(key: str) -> tuple[str | None, str]:
    attr_name = key.upper()
    if attr_name in os.environ:
        return str(os.environ.get(attr_name, "")), "config"
    env_file_map = _env_file_values()
    if attr_name in env_file_map:
        return str(env_file_map[attr_name]), "config"
    default_value = _settings_default_value(key)
    if default_value is not None:
        return default_value, "default"
    return None, "default"


def _resolve_setting_value(key: str, *, default: str = "") -> tuple[str, str]:
    db_val = _db_get(key)
    if db_val is not None:
        return db_val, "override"

    config_val, source = _config_get(key)
    if config_val is not None:
        if source == "config":
            return config_val, "config"
        if config_val != "" or default == "":
            return config_val, "default"
    return default, "default"


def get_setting_str(key: str, *, default: str = "") -> str:
    fallback = _SETTING_DEFAULTS.get(key, default)
    value, _source = _resolve_setting_value(key, default=fallback)
    return value


def get_setting_int(key: str, *, default: int = 0) -> int:
    raw = get_setting_str(key, default=str(default))
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def get_setting_bool(key: str, *, default: bool = False) -> bool:
    raw = get_setting_str(key, default="1" if default else "0").strip().lower()
    return raw in _BOOL_TRUE


def format_prompt_template(template: str, **kwargs) -> str:
    try:
        return template.format(**kwargs)
    except (KeyError, ValueError):
        return template


def admin_settings_payload() -> dict:
    groups: dict[str, list[dict]] = OrderedDict()
    for defn in SETTING_DEFINITIONS:
        key = defn["key"]
        group = str(defn.get("group", "General"))
        default_value = _SETTING_DEFAULTS.get(key, "")
        current, source = _resolve_setting_value(key, default=default_value)
        item = dict(defn)
        item["current_value"] = current
        item["source"] = source
        groups.setdefault(group, []).append(item)
    return {"groups": [{"name": group_name, "items": items} for group_name, items in groups.items()]}


def _coerce_value(defn: dict, raw_value: object) -> str:
    value_type = str(defn.get("type") or "string")
    text = "" if raw_value is None else str(raw_value)
    token = text.strip()
    key = str(defn.get("key") or "")

    if value_type == "int":
        try:
            parsed = int(token)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{key}: expected integer") from exc
        if defn.get("min") is not None and parsed < int(defn["min"]):
            raise ValueError(f"{key}: must be >= {defn['min']}")
        if defn.get("max") is not None and parsed > int(defn["max"]):
            raise ValueError(f"{key}: must be <= {defn['max']}")
        return str(parsed)

    if value_type == "bool":
        return "1" if token.lower() in _BOOL_TRUE else "0"

    if value_type == "choice":
        choices = [str(choice) for choice in (defn.get("choices") or [])]
        if token not in choices:
            raise ValueError(f"{key}: invalid option")
        return token

    if value_type == "text":
        return text

    return token


def save_admin_settings(values: dict, *, reset_keys: list[str] | None = None) -> dict:
    reset_keys = reset_keys or []
    defn_map = {d["key"]: d for d in SETTING_DEFINITIONS}

    with SessionLocal() as db:
        for key in reset_keys:
            key_str = str(key)
            row = db.query(AppSetting).filter(AppSetting.key == key_str).first()
            if row:
                db.delete(row)

        for key, raw_value in values.items():
            key_str = str(key)
            defn = defn_map.get(key_str)
            if not defn:
                raise ValueError(f"unknown setting key: {key_str}")
            value_str = _coerce_value(defn, raw_value)
            row = db.query(AppSetting).filter(AppSetting.key == key_str).first()
            if row:
                row.value = value_str
            else:
                db.add(AppSetting(key=key_str, value=value_str))

        db.commit()

    return admin_settings_payload()
