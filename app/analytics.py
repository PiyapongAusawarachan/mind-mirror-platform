"""Aggregations shared by student views and the teacher dashboard."""

from __future__ import annotations

from app import config
from app.models import Analysis, Assessment, LearningContext, MasterySnapshot


def mastery_from_distribution(dist: dict[str, int]) -> float:
    """Weighted mastery percentage from a level distribution."""

    total = sum(dist.get(level, 0) for level in config.LEVELS)
    if total == 0:
        return 0.0
    weighted = sum(dist.get(level, 0) * config.LEVEL_WEIGHT[level] for level in config.LEVELS)
    return round(weighted / total * 100, 1)


def record_snapshot(db, context: LearningContext, source: str, dist: dict[str, int]) -> MasterySnapshot:
    """Persist a point-in-time understanding mix for the timeline."""

    snap = MasterySnapshot(
        context_id=context.id,
        source=source,
        understood=dist.get(config.UNDERSTOOD, 0),
        confused=dist.get(config.CONFUSED, 0),
        not_understood=dist.get(config.NOT_UNDERSTOOD, 0),
        mastery_pct=mastery_from_distribution(dist),
    )
    db.add(snap)
    return snap


def timeline(context: LearningContext) -> list[dict]:
    """Chronological mastery points for a lesson."""

    points = []
    for snap in sorted(context.snapshots, key=lambda s: s.created_at):
        points.append(
            {
                "date": snap.created_at.strftime("%Y-%m-%d"),
                "source": snap.source,
                "mastery": snap.mastery_pct,
                "understood": snap.understood,
                "confused": snap.confused,
                "not_understood": snap.not_understood,
            }
        )
    return points


def latest_analysis(context: LearningContext) -> Analysis | None:
    if not context.analyses:
        return None
    return max(context.analyses, key=lambda a: a.created_at)


def latest_completed_assessment(context: LearningContext) -> Assessment | None:
    done = [a for a in context.assessments if a.completed_at is not None]
    if not done:
        return None
    return max(done, key=lambda a: a.completed_at)


def pre_levels(context: LearningContext) -> dict[str, str]:
    """Topic -> understanding level from the latest analysis (before assessment)."""

    analysis = latest_analysis(context)
    if analysis is None:
        return {}
    return {t.name: t.level for t in analysis.topics}


def post_levels(context: LearningContext) -> dict[str, str]:
    """Topic -> understanding level after the latest completed assessment."""

    assessment = latest_completed_assessment(context)
    if assessment is None:
        return {}
    result: dict[str, str] = {}
    for q in assessment.questions:
        if q.answer is not None:
            result[q.topic_name] = q.answer.resulting_level
    return result


def empty_distribution() -> dict[str, int]:
    return {level: 0 for level in config.LEVELS}


def context_distribution(context: LearningContext) -> dict[str, int]:
    dist = empty_distribution()
    for level in pre_levels(context).values():
        if level in dist:
            dist[level] += 1
    return dist


def improvement(context: LearningContext) -> dict[str, list[str]]:
    """Compare pre vs post levels: which weak topics improved, which still weak."""

    pre, post = pre_levels(context), post_levels(context)
    improved, still_weak = [], []
    rank = {config.NOT_UNDERSTOOD: 0, config.CONFUSED: 1, config.UNDERSTOOD: 2}
    for topic, before in pre.items():
        if before == config.UNDERSTOOD:
            continue
        after = post.get(topic)
        if after is None:
            continue
        if rank[after] > rank[before]:
            improved.append(topic)
        elif after != config.UNDERSTOOD:
            still_weak.append(topic)
    return {"improved": improved, "still_weak": still_weak}


def course_topic_distribution(contexts: list[LearningContext]) -> dict[str, dict[str, int]]:
    """Per-topic counts of understanding levels aggregated across contexts (T2)."""

    by_topic: dict[str, dict[str, int]] = {}
    for ctx in contexts:
        for topic, level in pre_levels(ctx).items():
            bucket = by_topic.setdefault(topic, empty_distribution())
            if level in bucket:
                bucket[level] += 1
    return by_topic


def course_timeline(contexts: list[LearningContext]) -> list[dict]:
    """Average mastery per date across all lessons in a course (long-term trend)."""

    by_date: dict[str, list[float]] = {}
    for ctx in contexts:
        for snap in ctx.snapshots:
            by_date.setdefault(snap.created_at.strftime("%Y-%m-%d"), []).append(snap.mastery_pct)
    return [
        {"date": date, "mastery": round(sum(vals) / len(vals), 1)}
        for date, vals in sorted(by_date.items())
    ]
