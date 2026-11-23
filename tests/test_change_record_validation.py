import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_canonical_goal_and_decision_ids_are_unique():
    goals = json.loads((ROOT/"data/36os/goals.json").read_text())["goals"]
    decisions = json.loads((ROOT/"data/36os/decisions.json").read_text())["decisions"]
    assert len({x["id"] for x in goals}) == len(goals)
    assert len({x["id"] for x in decisions}) == len(decisions)

def test_change_records_reference_known_goals_and_decisions():
    goals = {x["id"] for x in json.loads((ROOT/"data/36os/goals.json").read_text())["goals"]}
    decisions = {x["id"] for x in json.loads((ROOT/"data/36os/decisions.json").read_text())["decisions"]}
    for path in (ROOT/"data/36os/change-records").glob("*.json"):
        record = json.loads(path.read_text())
        assert record["goal_ids"] and set(record["goal_ids"]).issubset(goals)
        assert record["decision_ids"] and set(record["decision_ids"]).issubset(decisions)
        assert record["touched_files"]
