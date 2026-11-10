"""Generate a chronological incident record from structured evidence."""

from runtime import choice, cli, instant, report, rows, strings, text, unique, utc


def analyze(data):
    case_id = text(data.get("case_id"), "case_id")
    title = text(data.get("title"), "title")
    events = rows(data.get("events"), "events")
    actions = rows(data.get("actions", []), "actions")
    unique(events)
    unique(actions)
    known = {event["id"] for event in events}
    timeline = []
    for event in events:
        time = instant(event.get("timestamp"), "event.timestamp")
        timeline.append(
            {
                "type": "reported_event",
                "id": event["id"],
                "timestamp": utc(time),
                "source": text(event.get("source"), "event.source"),
                "description": text(event.get("description"), "event.description"),
            }
        )
    # Parse timestamps for ordering: fractional seconds must not be sorted lexically.
    timeline.sort(
        key=lambda event: (instant(event["timestamp"], "timestamp"), event["id"])
    )
    records = []
    for action in actions:
        refs = strings(action.get("evidence_ids"), "action.evidence_ids")
        if not refs or not set(refs).issubset(known):
            raise ValueError("actions must reference known evidence events")
        status = choice(
            action.get("status"),
            ["proposed", "approved", "executed", "verified"],
            "action.status",
        )
        record = {
            "type": "reported_action",
            "id": action["id"],
            "description": text(action.get("description"), "action.description"),
            "owner": text(action.get("owner"), "action.owner"),
            "reported_status": status,
            "evidence_ids": refs,
        }
        if status in ("executed", "verified"):
            record["executed_at"] = utc(
                instant(action.get("executed_at"), "action.executed_at")
            )
        if status == "verified":
            verification = strings(
                action.get("verification_evidence_ids"), "verification_evidence_ids"
            )
            if not verification or not set(verification).issubset(known):
                raise ValueError("verified actions require known verification evidence")
            record["verification_evidence_ids"] = verification
        records.append(record)
    unknowns = strings(data.get("unknowns", []), "unknowns")
    return report(
        "Incident Report Agent",
        {
            "case_id": case_id,
            "title": title,
            "events": len(timeline),
            "actions": len(records),
            "document_status": "draft_for_review",
        },
        timeline + records,
        unknowns
        + [
            "This report reflects caller-supplied records. Action statuses and source claims are not independently verified.",
            "The tool does not infer root cause, business impact, compromise, closure, or actions from chat markers.",
            "No report is posted or sent; JSON and Markdown are emitted locally for review.",
        ],
        [
            "Confirm the timeline, action status, evidence references and unresolved questions with the incident owner.",
            "Add a supported impact assessment and distinguish root cause from working hypotheses.",
            "Obtain the appropriate review before distributing the report or closing the incident.",
        ],
    )


if __name__ == "__main__":
    cli(analyze, __doc__)
