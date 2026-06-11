from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from evolving_creative_room.models import CreativeState, new_id, utc_now_iso


@dataclass(slots=True)
class EvolutionProposal:
    target_component: str
    failure_evidence: list[str]
    root_cause: str
    proposed_change: str
    expected_improvement: str
    risk: str
    validation_plan: str = ""
    predicted_metric: str = ""
    evidence_ids: list[str] = field(default_factory=list)
    rollback_plan: str = "Revert to the previous harness component version."
    proposal_id: str = field(default_factory=lambda: new_id("chg"))
    created_at: str = field(default_factory=utc_now_iso)
    status: str = "proposed"


@dataclass(slots=True)
class ChangeManifest:
    session_id: str
    proposals: list[EvolutionProposal]
    manifest_id: str = field(default_factory=lambda: new_id("manifest"))
    created_at: str = field(default_factory=utc_now_iso)

    def write(self, path: Path | str) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        return output


class HarnessEvolver:
    """AHE-style evolver."""

    def propose(self, state: CreativeState) -> ChangeManifest:
        proposals: list[EvolutionProposal] = []
        feedback_notes = [item.note for item in state.human_feedback if item.note]
        comments = [item.comment for item in state.comments]
        failure_evidence = [item.evidence_text for item in state.failure_signals]
        evidence_ids = [item.signal_id for item in state.failure_signals]

        if any("太模板" in note or "AI" in note for note in feedback_notes) or any(item.failure_type == "template_style" for item in state.failure_signals):
            proposals.append(
                EvolutionProposal(
                    target_component="harness/agents/draft_writer.md",
                    failure_evidence=failure_evidence or feedback_notes,
                    evidence_ids=evidence_ids,
                    root_cause="Draft language is perceived as templated or generic.",
                    proposed_change="Add anti-template rubric and user-approved examples.",
                    expected_improvement="Reduce manual rewrite distance and increase accept rate.",
                    risk="May become too informal for serious long-form tasks.",
                    validation_plan="Run template-sensitivity eval cases and compare critique count before keeping the rule.",
                    predicted_metric="fewer 'AI/模板' feedback signals in next 5 relevant sessions",
                )
            )

        if any("角色" in comment or "世界观" in comment for comment in comments):
            proposals.append(
                EvolutionProposal(
                    target_component="harness/agents/canon_keeper.md",
                    failure_evidence=comments,
                    root_cause="Narrative constraints need explicit continuity checks.",
                    proposed_change="Add canon consistency checklist before final rewrite.",
                    expected_improvement="Reduce out-of-character and timeline conflicts.",
                    risk="May slow down short social posts that only lightly reference canon.",
                    validation_plan="Run character/worldbuilding eval cases and check norm/canon comments.",
                    predicted_metric="lower canon warning count without reducing draft completion",
                )
            )

        if any(item.severity == "norm" for item in state.comments):
            proposals.append(
                EvolutionProposal(
                    target_component="harness/agents/norm_steward.md",
                    failure_evidence=[item.comment for item in state.comments if item.severity == "norm"],
                    root_cause="Norm advice must remain separate from creative preference.",
                    proposed_change="Record platform hard rules, soft conventions, and project rules separately.",
                    expected_improvement="Better traceability and fewer overblocking suggestions.",
                    risk="More nuanced output may require clearer UI grouping.",
                    validation_plan="Run platform adaptation eval cases and inspect risk grouping.",
                    predicted_metric="more precise norm comments with fewer generic warnings",
                )
            )

        if any(item.failure_type in {"over_explained", "generic_language", "repetitive_rhythm"} for item in state.failure_signals):
            proposals.append(
                EvolutionProposal(
                    target_component="harness/rubrics/creative_quality.md",
                    failure_evidence=[
                        item.evidence_text
                        for item in state.failure_signals
                        if item.failure_type in {"over_explained", "generic_language", "repetitive_rhythm"}
                    ],
                    evidence_ids=[
                        item.signal_id
                        for item in state.failure_signals
                        if item.failure_type in {"over_explained", "generic_language", "repetitive_rhythm"}
                    ],
                    root_cause="Quality review needs a stronger boundary between final copy and process explanation.",
                    proposed_change="Add a naturalness rubric that flags process notes, generic adjectives, and repetitive rhythm as review-only issues.",
                    expected_improvement="Improve naturalness score without adding fixed replacement phrases.",
                    risk="Over-penalizing explanatory drafts may reduce useful scaffolding in early ideation sessions.",
                    validation_plan="Run naturalness-sensitive eval cases and compare naturalness_delta before applying.",
                    predicted_metric="naturalness_score improves while expected signal coverage remains stable",
                )
            )

        if not proposals:
            proposals.append(
                EvolutionProposal(
                    target_component="harness/rubrics/creative_quality.md",
                    failure_evidence=["No strong failure pattern yet."],
                    root_cause="Insufficient feedback evidence for targeted harness edits.",
                    proposed_change="Collect accept/reject/edit signals for more sessions before changing behavior.",
                    expected_improvement="Avoid premature self-modification.",
                    risk="System may feel slower to personalize at the beginning.",
                    validation_plan="Wait for stronger human feedback evidence before applying.",
                    predicted_metric="more evidence-linked proposals",
                )
            )

        return ChangeManifest(session_id=state.session_id, proposals=proposals)

    def apply_proposal(
        self,
        *,
        project_root: Path | str,
        manifest: dict[str, object],
        proposal_id: str,
        reviewer_note: str = "",
    ) -> dict[str, object]:
        project_root = Path(project_root).resolve()
        harness_root = (project_root / "harness").resolve()
        proposal = _find_proposal(manifest, proposal_id)
        proposal = _normalize_proposal(proposal)
        target = (project_root / str(proposal["target_component"])).resolve()
        if not _is_relative_to(target, harness_root):
            raise ValueError("Evolution proposals may only edit files under harness/.")
        if not target.exists():
            raise FileNotFoundError(str(target))

        amendment = _render_amendment(manifest, proposal, reviewer_note)
        original = target.read_text(encoding="utf-8")
        target.write_text(original.rstrip() + "\n\n" + amendment + "\n", encoding="utf-8")

        log_dir = project_root / ".ecr_workspace" / "evolution_applied"
        log_dir.mkdir(parents=True, exist_ok=True)
        log = {
            "applied_at": utc_now_iso(),
            "manifest_id": manifest.get("manifest_id"),
            "session_id": manifest.get("session_id"),
            "proposal_id": proposal_id,
            "target_component": proposal["target_component"],
            "reviewer_note": reviewer_note,
            "validation_plan": proposal.get("validation_plan", ""),
            "predicted_metric": proposal.get("predicted_metric", ""),
            "diff_summary": proposal.get("proposed_change", ""),
            "rollback_target": proposal.get("rollback_plan", ""),
            "status": "applied_pending_validation",
        }
        log_path = log_dir / f"{proposal_id}.json"
        log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
        return log


def _find_proposal(manifest: dict[str, object], proposal_id: str) -> dict[str, object]:
    proposals = manifest.get("proposals", [])
    if not isinstance(proposals, list):
        raise ValueError("Manifest proposals are invalid.")
    for proposal in proposals:
        if isinstance(proposal, dict) and proposal.get("proposal_id") == proposal_id:
            return proposal
    raise ValueError(f"Proposal not found: {proposal_id}")


def _normalize_proposal(proposal: dict[str, object]) -> dict[str, object]:
    if not proposal.get("proposed_change") and proposal.get("targeted_fix"):
        proposal = dict(proposal)
        proposal["proposed_change"] = proposal.get("targeted_fix")
    if not proposal.get("risk") and proposal.get("regression_risk"):
        proposal = dict(proposal)
        proposal["risk"] = proposal.get("regression_risk")
    return proposal


def _render_amendment(manifest: dict[str, object], proposal: dict[str, object], reviewer_note: str) -> str:
    evidence = proposal.get("failure_evidence", [])
    evidence_lines = "\n".join(f"- {item}" for item in evidence if isinstance(item, str)) or "- 无"
    note = reviewer_note.strip() or "人工确认应用。"
    return (
        "## Evolution Amendment\n\n"
        f"- 时间：{utc_now_iso()}\n"
        f"- Manifest：{manifest.get('manifest_id')}\n"
        f"- Proposal：{proposal.get('proposal_id')}\n"
        f"- 审批说明：{note}\n\n"
        "### 证据\n\n"
        f"{evidence_lines}\n\n"
        "### 根因\n\n"
        f"{proposal.get('root_cause')}\n\n"
        "### 新规则\n\n"
        f"{proposal.get('proposed_change')}\n\n"
        "### 预期收益\n\n"
        f"{proposal.get('expected_improvement')}\n\n"
        "### 回归风险\n\n"
        f"{proposal.get('risk')}\n\n"
        "### 回滚计划\n\n"
        f"{proposal.get('rollback_plan', 'Revert to the previous harness component version.')}\n"
    )


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
