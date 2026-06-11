from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(slots=True)
class NaturalnessProfile:
    score: float
    signals: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)


def evaluate_naturalness(
    text: str,
    *,
    request: str = "",
    feedback: list[str] | None = None,
    platforms: list[str] | None = None,
) -> NaturalnessProfile:
    """Diagnose naturalness risks without generating replacement copy."""

    normalized = re.sub(r"\s+", " ", text).strip()
    feedback_text = " ".join(item for item in (feedback or []) if item)
    platforms = platforms or []
    penalties: list[tuple[str, float, str, str]] = []

    if not normalized:
        return NaturalnessProfile(score=0.0, signals=["empty_draft"], notes=["草稿为空。"])

    template_hits = _hits(
        normalized,
        [
            "引发广泛关注",
            "不容错过",
            "重磅来袭",
            "强势登场",
            "带来全新体验",
            "让我们一起",
            "敬请期待",
            "精彩纷呈",
        ],
    )
    if len(template_hits) >= 2:
        penalties.append(("template_style", 0.18, "出现多处固定营销/模板表达。", "、".join(template_hits[:3])))

    explanation_hits = _hits(
        normalized,
        [
            "以下是基于",
            "编辑版本",
            "具体调整如下",
            "创作方向：",
            "初稿：",
            "编辑建议：",
            "变更说明",
            "待讨论方向",
            "请确认偏好",
            "如果这是",
            "下一轮应",
            "需要用户反馈",
        ],
    )
    if len(explanation_hits) >= 2:
        penalties.append(("over_explained", 0.16, "正文混入了系统说明或创作过程说明。", "、".join(explanation_hits[:3])))

    if _repeat_ratio(normalized) > 0.18:
        penalties.append(("repetitive_rhythm", 0.1, "短语重复偏高，读起来容易机械。", "重复短语比例偏高"))

    if any(item in feedback_text for item in ["第二段", "标题", "开头", "结尾"]) and not _mentions_feedback_target(normalized, feedback_text):
        penalties.append(("feedback_target_missed", 0.14, "用户反馈指定了对象，但最新稿缺少对应修改痕迹。", feedback_text[:80]))

    if platforms and any(term in normalized for term in ["硬广", "种草神器", "闭眼入", "必买", "冲就完了"]):
        penalties.append(("platform_overfit", 0.14, "平台表达压过了原始语境，可能显得硬。", "、".join(platforms)))

    if _generic_density(normalized) > 0.16:
        penalties.append(("generic_language", 0.1, "泛化形容偏多，缺少具体对象或场景支撑。", "泛化词密度偏高"))

    score = 1.0 - sum(item[1] for item in penalties)
    score = round(max(0.0, min(1.0, score)), 3)
    if not penalties:
        return NaturalnessProfile(score=score, notes=["未发现明显模板化或反馈响应风险。"])
    return NaturalnessProfile(
        score=score,
        signals=[item[0] for item in penalties],
        notes=[item[2] for item in penalties],
        evidence=[item[3] for item in penalties],
    )


def _hits(text: str, terms: list[str]) -> list[str]:
    return [term for term in terms if term in text]


def _repeat_ratio(text: str) -> float:
    chunks = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,6}", text)
    if len(chunks) < 16:
        return 0.0
    seen: set[str] = set()
    repeats = 0
    for chunk in chunks:
        if chunk in seen:
            repeats += 1
        seen.add(chunk)
    return repeats / max(len(chunks), 1)


def _mentions_feedback_target(text: str, feedback_text: str) -> bool:
    target_terms = [term for term in ["第二段", "标题", "开头", "结尾"] if term in feedback_text]
    if not target_terms:
        return True
    return any(term in text for term in target_terms)


def _generic_density(text: str) -> float:
    terms = ["独特", "丰富", "精彩", "全新", "沉浸", "极致", "多元", "深度", "温度", "张力", "记忆点"]
    total = max(len(re.findall(r"[\u4e00-\u9fff]{2}", text)), 1)
    hits = sum(text.count(term) for term in terms)
    return hits / total
