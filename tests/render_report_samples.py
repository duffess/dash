"""Generate offline HTML fixtures for browser/print QA, without database or API calls."""
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.utils.report_demo import demo_snapshot, SCENARIOS
from app.utils.report_export import render_report_html


if __name__ == "__main__":
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=True)
    for scenario, label in SCENARIOS.items():
        row = SimpleNamespace(title=label, snapshot=demo_snapshot(scenario),
                              created_at=datetime.now(timezone.utc), analysis=None, ai_model=None)
        html = render_report_html(row)
        (output / f"{scenario}.html").write_text(html, encoding="utf-8")
        (output / f"{scenario}.json").write_text(json.dumps(dict(
            id="demo-" + scenario, client_id="demo", client_name=row.snapshot["client_name"],
            title=row.title, created_at=row.created_at.isoformat(), snapshot=row.snapshot,
            analysis=None, ai_model=None, rendered_html=html,
        ), ensure_ascii=False), encoding="utf-8")
    print(f"Rendered {len(SCENARIOS)} offline HTML samples")
