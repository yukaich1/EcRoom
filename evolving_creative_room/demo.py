from __future__ import annotations

from pathlib import Path

from evolving_creative_room.orchestration import CreativeRoomRunner


def main() -> None:
    runner = CreativeRoomRunner(Path(".ecr_workspace"))
    state = runner.run_seed_session(
        request="帮我写一个新角色登场文案，最好能顺便发微博宣传，但不要太像模板。",
        user_preferences=["不喜欢用力过猛的营销腔", "喜欢有一点角色张力但不要中二"],
        feedback_note="初稿方向可以，但有些地方太像 AI 文案，需要更自然。",
    )
    print("EcRoom seed session complete.")
    print(f"Session: {state.session_id}")
    print(f"Intent: {state.intent.summary()}")
    print(f"Drafts: {len(state.drafts)}")
    print(f"Comments: {len(state.comments)}")
    print("Workspace: .ecr_workspace")


if __name__ == "__main__":
    main()
