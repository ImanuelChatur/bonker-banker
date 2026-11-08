"""Home page data: one headline stat for the hero."""
import logging

from ._placeholders import engine_fn, is_placeholder

log = logging.getLogger(__name__)


def home_stat() -> dict | None:
    """Population headline. Uses engine.insights.headline() once it exists; until then the real stress numbers
    from engine.findings (never placeholder numbers on the home page)."""
    try:
        if not is_placeholder("insights", "headline"):
            h = engine_fn("insights", "headline")()
            return {"big": f"{h['pct_runout_6m']:g}%", "text": h["text"], "scenario": h.get("scenario")}
        from engine.findings import biggest_finding
        f = biggest_finding()
        job = next((s for s in f["stress"] if s["name"].lower().startswith("job loss, ei")), None)
        if not job:
            return None
        today = f["stress"][0]["share_pct"]
        return {"big": f"{job['share_pct']:g}%",
                "text": f"of all {f['n_accounts']:,} accounts would run out of savings within 6 months of a job loss "
                        f"on EI, up from {today:g}% today.",
                "scenario": "EI at 55% of income for 6 months"}
    except Exception as e:  # the home page must always render
        log.warning("Home headline unavailable: %s", e)
        return None
