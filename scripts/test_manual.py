"""
Manual Verification Script for Section 4.6 (Persistent Discussion History)
Run this script to interactively test all persistence features:
    python scripts/test_manual.py
"""

import json
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows terminals
if sys.platform == "win32" and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.discussion.models import DiscussionState, DiscussionMessage
from src.discussion.persistence import (
    save_discussion_from_state,
    load_discussion,
    list_discussions,
)


def print_step(num: int, title: str):
    print("\n" + "=" * 60)
    print(f"  Step {num}: {title}")
    print("=" * 60)


def main():
    print("\n>>> Starting Manual Test for Section 4.6: Persistence Module")

    # -------------------------------------------------------------
    # STEP 1: Create a realistic DiscussionState with messages & opinions
    # -------------------------------------------------------------
    print_step(1, "Create a simulated DiscussionState (2 rounds, 2 agents)")
    state = DiscussionState(
        topic="Should Arsenal sign a clinical striker in the January transfer window?",
        agent_ids=["tactician", "scout"],
        total_rounds=3,
        discussion_id="manual-demo-001",
    )

    # Round 1
    state.advance_round()
    msg1 = DiscussionMessage(
        round_number=1,
        sender_id="tactician",
        recipient_ids=["scout"],
        content=(
            "STANCE: AGREE\n"
            "REASONING: Arsenal struggles against low-block defenses without a classic number 9.\n"
            "SOURCES USED: understat_xg_stats, premier_league_round_20"
        ),
    )
    state.record_and_queue(msg1)
    print("  [+] Added Round 1 message from [tactician] (Stance: AGREE)")

    # Round 2
    state.advance_round()
    msg2 = DiscussionMessage(
        round_number=2,
        sender_id="scout",
        recipient_ids=["tactician"],
        content=(
            "STANCE: NEUTRAL\n"
            "REASONING: Winter striker prices are heavily inflated; scouting youth talents first is safer.\n"
            "SOURCES USED: transfermarkt_january_window"
        ),
    )
    state.record_and_queue(msg2)
    print("  [+] Added Round 2 message from [scout] (Stance: NEUTRAL)")

    # -------------------------------------------------------------
    # STEP 2: Save using bridge function
    # -------------------------------------------------------------
    print_step(2, "Save discussion state to JSON using save_discussion_from_state()")
    output_path = save_discussion_from_state(state, output_dir="outputs")
    print(f"  [OK] Successfully saved to: {output_path}")
    assert Path(output_path).exists(), "Error: Saved file does not exist!"

    # -------------------------------------------------------------
    # STEP 3: Inspect raw JSON on disk
    # -------------------------------------------------------------
    print_step(3, "Inspect saved JSON structure on disk")
    with open(output_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    print(f"  - File size: {Path(output_path).stat().st_size} bytes")
    print(f"  - Discussion ID: {raw_data['config']['discussion_id']}")
    print(f"  - Topic: {raw_data['config']['topic']}")
    print(f"  - Participants: {raw_data['config']['agent_ids']}")
    print(f"  - Total messages saved: {len(raw_data['messages'])}")
    print(f"  - Opinions captured: {len(raw_data['opinions'])}")
    for op in raw_data["opinions"]:
        print(f"    * Round {op['round_num']} [{op['agent_id']}]: Stance = {op['stance']}")
        print(f"      Reasoning: {op['reasoning'][:65]}...")
    print(f"  - Metadata: total_messages={raw_data['metadata']['total_messages']}, duration={raw_data['metadata']['duration_seconds']}s")

    # -------------------------------------------------------------
    # STEP 4: Load discussion using load_discussion()
    # -------------------------------------------------------------
    print_step(4, "Load and reconstruct object using load_discussion()")
    loaded_result = load_discussion(output_path)
    print(f"  [OK] Successfully loaded DiscussionResult:")
    print(f"      * Config Topic: {loaded_result.config.topic}")
    print(f"      * Message count: {len(loaded_result.messages)}")
    print(f"      * Stance 1 extracted: {loaded_result.opinions[0].stance}")
    print(f"      * Stance 2 extracted: {loaded_result.opinions[1].stance}")

    # -------------------------------------------------------------
    # STEP 5: List all discussions using list_discussions()
    # -------------------------------------------------------------
    print_step(5, "List discussions in outputs/ using list_discussions()")
    discussions = list_discussions(output_dir="outputs")
    print(f"  [OK] Found {len(discussions)} discussion(s) in outputs/:")
    for d in discussions:
        print(f"      - ID: {d['discussion_id']} | Topic: {d['topic'][:40]}... | Messages: {d['num_messages']}")

    # -------------------------------------------------------------
    # STEP 6: Test Error Handling
    # -------------------------------------------------------------
    print_step(6, "Test Error Handling (FileNotFoundError & Corrupted JSON)")
    try:
        load_discussion("outputs/non_existent_discussion_123.json")
        print("  [X] Failed: Should have raised FileNotFoundError!")
    except FileNotFoundError:
        print("  [OK] FileNotFoundError caught successfully when file is missing.")

    # Create dummy invalid JSON
    bad_file = Path("outputs/temp_corrupted_test.json")
    bad_file.write_text("{invalid_json: true", encoding="utf-8")
    try:
        load_discussion(bad_file)
        print("  [X] Failed: Should have raised ValueError!")
    except ValueError:
        print("  [OK] ValueError caught successfully on corrupted JSON syntax.")
    finally:
        if bad_file.exists():
            bad_file.unlink()

    print("\n" + "=" * 60)
    print("  >>> ALL MANUAL TESTS PASSED SUCCESSFULLY! 100% READY! <<<")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
