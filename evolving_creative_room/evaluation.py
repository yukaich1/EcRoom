from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from evolving_creative_room.models import CreativeState, new_id, utc_now_iso
from evolving_creative_room.naturalness import evaluate_naturalness


@dataclass(slots=True)
class EvalCase:
    name: str
    request: str
    preferences: list[str] = field(default_factory=list)
    expected_signals: list[str] = field(default_factory=list)
    cluster: str = "general"


@dataclass(slots=True)
class EvalResult:
    case_name: str
    session_id: str
    score: float
    notes: list[str]
    naturalness_score: float = 0.0
    coverage_score: float = 0.0


@dataclass(slots=True)
class EvalRun:
    run_id: str
    created_at: str
    results: list[EvalResult]
    kind: str = "single"
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def average_score(self) -> float:
        if not self.results:
            return 0.0
        return round(sum(item.score for item in self.results) / len(self.results), 3)


DEFAULT_EVAL_CASES = [
    EvalCase(
        name="社媒与角色混合",
        request="写一个新角色登场文案，适合发微博宣传，冷一点，不要太模板。",
        preferences=["克制", "不要中二"],
        expected_signals=["微博", "角色", "模板"],
        cluster="publish_ready_eval",
    ),
    EvalCase(
        name="小红书生活分享",
        request="写一篇小红书风格的体验笔记，主题是一个安静的夜间阅读角。",
        preferences=["自然", "不夸张"],
        expected_signals=["小红书", "真实", "自然"],
        cluster="publish_ready_eval",
    ),
    EvalCase(
        name="世界观说明",
        request="帮我写一段游戏世界观设定，描述一座被潮汐钟控制的城市。",
        preferences=["有画面", "不要解释太满"],
        expected_signals=["世界观", "城市", "设定"],
        cluster="canon_eval",
    ),
    EvalCase(
        name="去模板改稿",
        request="把这段角色宣传改得更像人写的，别有 AI 味，保留冷淡语气。",
        preferences=["自然", "克制", "不要模板"],
        expected_signals=["角色", "自然", "模板"],
        cluster="naturalness_eval",
    ),
    EvalCase(
        name="反馈对象定位",
        request="把第二段改得更自然，标题保持不变，整体不要变成硬广。",
        preferences=["本次只改第二段", "不要硬广"],
        expected_signals=["第二段", "标题", "自然"],
        cluster="revision_eval",
    ),
    EvalCase(
        name="临时偏好边界",
        request="这次先写得热闹一点，但不要记成我的长期风格。",
        preferences=["这次热闹一点", "不要记成长期偏好"],
        expected_signals=["这次", "长期", "风格"],
        cluster="memory_boundary_eval",
    ),
]


class EvaluationStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.path = self.root / "evaluations"
        self.path.mkdir(parents=True, exist_ok=True)

    def write(self, run: EvalRun) -> Path:
        path = self.path / f"{run.run_id}.json"
        payload = {
            "run_id": run.run_id,
            "created_at": run.created_at,
            "kind": run.kind,
            "average_score": run.average_score,
            "metadata": run.metadata,
            "results": [asdict(item) for item in run.results],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def list(self, limit: int = 20) -> list[dict[str, object]]:
        runs = []
        for path in sorted(self.path.glob("eval_*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            runs.append(json.loads(path.read_text(encoding="utf-8")))
        return runs[:limit]


def score_state(state: CreativeState, expected_signals: list[str]) -> EvalResult:
    notes = []
    latest = state.drafts[-1].content if state.drafts else ""
    profile = evaluate_naturalness(
        latest,
        request=state.intent.raw_request,
        feedback=[item.note for item in state.human_feedback if item.note],
    )
    score = 0.0
    if latest and len(latest) >= 40:
        score += 0.25
    else:
        notes.append("草稿过短。")
    if state.comments:
        score += 0.2
    else:
        notes.append("缺少 agent 评论。")
    if state.intent.constraints:
        score += 0.2
    else:
        notes.append("缺少约束识别。")
    matched = [signal for signal in expected_signals if signal in latest or signal in state.intent.raw_request or signal in " ".join(state.intent.constraints)]
    coverage = len(matched) / max(len(expected_signals), 1)
    if matched:
        score += 0.25 * coverage
    else:
        notes.append("草稿没有体现预期信号。")
    score += 0.1 * profile.score
    if profile.score < 0.75:
        notes.extend(profile.notes)
    if not notes:
        notes.append("通过基础可用性检查。")
    return EvalResult(
        case_name="",
        session_id=state.session_id,
        score=round(min(score, 1.0), 3),
        notes=notes,
        naturalness_score=profile.score,
        coverage_score=round(coverage, 3),
    )


def new_eval_run(results: list[EvalResult], *, kind: str = "single", metadata: dict[str, object] | None = None) -> EvalRun:
    return EvalRun(run_id=new_id("eval"), created_at=utc_now_iso(), results=results, kind=kind, metadata=metadata or {})


def compare_eval_runs(baseline: EvalRun, candidate: EvalRun) -> dict[str, object]:
    delta = round(candidate.average_score - baseline.average_score, 3)
    baseline_by_case = {item.case_name: item for item in baseline.results}
    rows = []
    for item in candidate.results:
        base = baseline_by_case.get(item.case_name)
        rows.append(
            {
                "case_name": item.case_name,
                "baseline_score": base.score if base else None,
                "candidate_score": item.score,
                "delta": round(item.score - base.score, 3) if base else None,
                "baseline_naturalness": base.naturalness_score if base else None,
                "candidate_naturalness": item.naturalness_score,
                "naturalness_delta": round(item.naturalness_score - base.naturalness_score, 3) if base else None,
                "baseline_coverage": base.coverage_score if base else None,
                "candidate_coverage": item.coverage_score,
                "coverage_delta": round(item.coverage_score - base.coverage_score, 3) if base else None,
                "baseline_notes": base.notes if base else [],
                "candidate_notes": item.notes,
            }
        )
    readiness, readiness_reasons = _readiness(delta, rows)
    return {
        "baseline_run_id": baseline.run_id,
        "candidate_run_id": candidate.run_id,
        "baseline_average": baseline.average_score,
        "candidate_average": candidate.average_score,
        "delta": delta,
        "decision": readiness,
        "readiness": readiness,
        "readiness_reasons": readiness_reasons,
        "cases": rows,
    }


def _readiness(delta: float, rows: list[dict[str, object]]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if delta < 0:
        reasons.append("候选平均分低于 baseline。")
    naturalness_regressions = [
        row["case_name"]
        for row in rows
        if isinstance(row.get("naturalness_delta"), (int, float)) and float(row["naturalness_delta"]) < -0.05
    ]
    if naturalness_regressions:
        reasons.append("自然度回退：" + "、".join(naturalness_regressions))
    coverage_regressions = [
        row["case_name"]
        for row in rows
        if isinstance(row.get("coverage_delta"), (int, float)) and float(row["coverage_delta"]) < -0.1
    ]
    if coverage_regressions:
        reasons.append("需求覆盖回退：" + "、".join(coverage_regressions))
    if not reasons and delta > 0:
        return "applicable", ["候选平均分提升，且自然度与需求覆盖未明显回退。"]
    if not reasons:
        return "needs_review", ["候选与 baseline 接近，需要人工结合具体 case 判断。"]
    return "blocked", reasons


def validate_evolution_prediction(*, predicted_metric: str, later_feedback: list[str], later_comments: list[str]) -> dict[str, object]:
    text = " ".join([*later_feedback, *later_comments])
    if not predicted_metric.strip():
        return {"status": "needs_more_data", "matched": False, "reason": "没有预测指标。"}
    repeated_failure = any(term in text for term in ["太模板", "AI", "角色不对", "世界观不对", "风险太泛", "规范太泛"])
    return {
        "status": "validated" if text and not repeated_failure else "needs_more_data",
        "matched": bool(text and not repeated_failure),
        "reason": "后续反馈暂未出现同类失败信号。" if text and not repeated_failure else "还需要更多后续反馈验证。",
        "predicted_metric": predicted_metric,
    }
