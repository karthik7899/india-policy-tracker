import asyncio
import datetime
import sys
import aiohttp
from config import load_watchlist, save_watchlist, SECTOR_METADATA
from logger import log
from scraper import (
    fetch_all_feeds_async,
    fetch_global_event_feeds_async,
    fetch_state_policy_async,
    scrape_pib_pli_approvals_async,
    fetch_advanced_rss_feeds_async,
    check_sebi_sid_filings_async,
    fetch_institutional_activity_async,
    fetch_exchange_filings_async,
)
from analysis.growth import update_live_stock_prices, apply_liquidity
from analysis.rotation import auto_curate_watchlist
from dashboard.builder import build_dashboard_views
from providers.screener import fetch_all_screener_fundamentals
from emails.mailer import build_briefing_email, send_email
from analysis import revisions as revisions_mod
from analysis import last_good
from analysis import postmortem
from analysis import reader_runtime
from analysis.thesis import compute_thesis_health
from analysis.variant_perception import compute_variant_perception
from analysis.curve_stage import classify_sector_curve_stage
from analysis.market_share import (
    compute_industry_share,
    snapshot_prior_industry_shares,
)
from entities import find_duplicate_holdings
from providers.nse_delivery import apply_delivery, fetch_delivery_async
from providers.isin_master import (
    load_isin_master,
    load_registered_names,
    refresh_isin_master_async,
    annotate_watchlist_isins,
)
from analysis import company_names


def save_data_for_dashboard(brief_data, watchlist):
    """Write the run's two outputs.

    history.json keeps the full corpus for the next run's deduplication and
    for the four consumers that read the accumulated feeds; dashboard_data.json
    carries a trimmed display copy, because the browser downloads it whole on
    every page load. Splitting them means nothing done for the dashboard's
    sake can shrink what the pipeline computes on.
    """
    from dashboard.payload import build_display_payload
    from dashboard.sidecars import write_sidecars
    from history.store import HistoryStore
    from utils import atomic_write_json

    HistoryStore().save(brief_data)

    # Two steps, kept apart on purpose. build_display_payload is a pure
    # transform of the corpus into a display copy; write_sidecars puts files on
    # disk. Folding the write into the builder gave every test that called it a
    # side effect on the working tree, which is how a "build" function ends up
    # owning half the I/O in a module.
    display = build_display_payload(brief_data, watchlist)
    display, _sidecar_files = write_sidecars(display)

    output = {
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "watchlist": watchlist,
        "sectors": SECTOR_METADATA,
        "briefing": display,
    }
    atomic_write_json(output, "dashboard_data.json")

    log.info(
        "SUCCESS: Updated data saved to 'dashboard_data.json' for web dashboard display."
    )


async def run_pipeline():
    # NOTE: this pipeline intentionally mixes two concurrency models:
    # asyncio/aiohttp for the scrapers and Screener, and
    # ThreadPoolExecutor/requests for yfinance (which is sync-only).
    # Don't refactor one into the other — yfinance can't be awaited, and the
    # scrapers gain nothing from threads.
    watchlist = load_watchlist()

    # Stamp each holding's ISIN from the committed symbol→ISIN master so
    # identity-keyed features (rotation's duplicate guard, the duplicate-
    # holding check below) work from the first line of the run, offline.
    isin_master = load_isin_master()
    annotate_watchlist_isins(watchlist, isin_master)

    # Names before anything matches on them: a name cut down from the
    # registered one ("NTPC Green Ene.") matches no headline but by ticker
    # (analysis/company_names.py).
    registered_names = load_registered_names()
    renamed = company_names.repair_holding_names(watchlist, registered_names)
    if renamed:
        log.info(
            f"Names: {len(renamed)} holding(s) renamed to their registered "
            "names: " + "; ".join(f"{t} '{old}' -> '{new}'" for t, old, new in renamed)
        )
    unchecked = [
        f"{s['ticker']} '{s['name']}'"
        for sec, stocks in watchlist.items()
        if sec != "macro_indicators" and isinstance(stocks, list)
        for s in stocks
        if isinstance(s, dict)
        and s.get("name")
        and str(s.get("ticker", "")).upper() not in registered_names
        and company_names.looks_shortened(s["name"])
    ]
    if unchecked:
        log.warning(
            "Names: cut down, and NSE's list has no name to repair them from: "
            + ", ".join(unchecked)
        )

    # Snapshot targets/coverage before anything mutates the watchlist, so
    # estimate-revision momentum can diff "before this run" vs "after".
    prior_estimates = revisions_mod.snapshot_prior_estimates(watchlist)
    # And every fetched value, so one a source fails to deliver this run can
    # be put back, marked, rather than lost (analysis/last_good.py).
    prior_values = last_good.snapshot(watchlist)
    prior_industry_shares = snapshot_prior_industry_shares(watchlist)
    # Challengers the radar flagged before: searched for and compared with
    # their sector's holdings after their headline has aged out.
    from analysis import entrant_watch

    watched_entrants = entrant_watch.load_watched()

    # Gather news data async
    data = await fetch_all_feeds_async()

    # Rotation runs before the Screener fetch (so anything it adds gets
    # fundamentals the same run), which means this run's peer tables do not
    # exist yet. The previous run's are already committed in
    # dashboard_data.json and are screened on quarterly fundamentals, so a
    # day of staleness costs nothing.
    from history.store import HistoryStore
    from analysis.candidate_screen import (
        candidates_for_rotation,
        screen_sector_candidates,
    )

    prior = HistoryStore().data.get("briefing", {})
    prior_screened = screen_sector_candidates(
        prior.get("peer_competitors") or {},
        known_symbols=set(isin_master),
    )

    # Holdings before rotation, for the "since the last run" strip.
    held_before = {
        str(st.get("ticker")).upper()
        for sec, stocks in watchlist.items()
        if sec != "macro_indicators" and isinstance(stocks, list)
        for st in stocks
        if isinstance(st, dict) and st.get("ticker")
    }

    # Auto-curate the watchlist (discovers emerging players and rotates stocks)
    emerging, rotation_decisions = auto_curate_watchlist(
        data, watchlist, screened_candidates=candidates_for_rotation(prior_screened)
    )
    data["emerging_players"] = emerging

    rotation_ledger = postmortem.load_ledger()
    for decision in rotation_decisions:
        postmortem.log_decision(
            rotation_ledger, decision["action"], decision["sector"], decision["stock"]
        )

    # Fetch live Yahoo Finance prices
    live_prices = update_live_stock_prices(watchlist)
    # Weekly closes go to the company digest, not into the freshness record.
    weekly_closes = live_prices.pop("weekly_closes", {}) or {}
    data["freshness"] = {"live_prices": live_prices}

    # Fetch Screener.in fundamentals async; also returns Screener's industry
    # peer tables — a competitor-discovery channel independent of headlines.
    peer_competitors, industry_tables = await fetch_all_screener_fundamentals(
        watchlist, entrants=entrant_watch.screener_entrants(watched_entrants)
    )
    # Screener's peer tables cut long names to about fifteen characters, and
    # these rows are both shown and matched against headlines.
    competitors_renamed = company_names.name_rows(peer_competitors, registered_names)
    if competitors_renamed:
        log.info(f"Names: {competitors_renamed} competitor(s) given registered names.")
    data["peer_competitors"] = peer_competitors or {}
    data["candidate_screen"] = screen_sector_candidates(
        peer_competitors or {}, known_symbols=set(isin_master)
    )

    # The Screener fetch rebuilds each stock's screener dict from scratch,
    # dropping the ISIN stamped above — re-annotate so identity survives
    # into the duplicate check and the committed watchlist.
    isin_covered = annotate_watchlist_isins(watchlist, isin_master)
    log.info(f"ISIN coverage: {isin_covered} holdings keyed by ISIN.")

    # Turnover is re-applied here for the same reason ISIN is: it was computed
    # during the price fetch above, and the Screener fetch has just replaced
    # the dict it lives in.
    liquidity_applied = apply_liquidity(watchlist)
    log.info(f"Liquidity: turnover attached to {liquidity_applied} holding(s).")

    # Delivery percentage separates real accumulation from intraday churn,
    # which volume-derived turnover cannot. Fetched and applied here, after
    # the Screener rebuild, for the same reason turnover is: that fetch
    # replaces the dict wholesale.
    async with aiohttp.ClientSession() as delivery_session:
        delivery_rows = await fetch_delivery_async(delivery_session)
    delivery_applied = apply_delivery(watchlist, delivery_rows)
    log.info(f"Delivery: attached to {delivery_applied} holding(s).")

    # Every live source has now written. A value one of them failed to
    # deliver is put back if it is under a week old, and marked as kept, so
    # nothing downstream reads a timeout as a company with no fundamentals.
    kept = last_good.restore(watchlist, prior_values)
    data["freshness"]["last_good"] = kept
    log.info(last_good.describe(kept))

    # True industry market share: each holding's slice of its FULL Screener
    # industry peer group's quarterly sales, not just the watchlist subset.
    data["industry_share"] = compute_industry_share(
        watchlist, industry_tables, prior_industry_shares
    )

    # Safety net: ISIN identifies each holding uniquely, so the same company
    # silently ending up tracked under two sectors — as DIXON was, until this
    # check existed — surfaces as a log warning the same run it happens
    # instead of persisting unnoticed.
    duplicate_holdings = find_duplicate_holdings(watchlist)
    for dup in duplicate_holdings:
        holdings_desc = ", ".join(
            f"{h['ticker']} ({h['sector']})" for h in dup["holdings"]
        )
        log.warning(f"Duplicate holding detected (ISIN {dup['isin']}): {holdings_desc}")

    # Estimate each holding's share of tracked peer-group revenue and its trend
    from analysis.market_share import compute_peer_market_share

    data["market_share"] = compute_peer_market_share(watchlist)

    # Gather additional policy and institutional feeds asynchronously
    async with aiohttp.ClientSession() as session:
        log.info("Starting concurrent policy and institutional feeds scraping...")
        pli_task = scrape_pib_pli_approvals_async(
            session, watchlist, registered=registered_names
        )
        adv_rss_task = fetch_advanced_rss_feeds_async(session, watchlist)
        sebi_task = check_sebi_sid_filings_async(session)
        inst_task = fetch_institutional_activity_async(session, watchlist)
        held_exchange_filings: list = []
        filings_task = fetch_exchange_filings_async(
            session, watchlist, held_out=held_exchange_filings
        )
        isin_refresh_task = refresh_isin_master_async(
            session, isin_master, names=registered_names
        )
        global_events_task = fetch_global_event_feeds_async(
            session,
            holdings=[
                st.get("ticker")
                for sec, stocks in watchlist.items()
                if isinstance(stocks, list)
                for st in stocks
                if isinstance(st, dict) and st.get("ticker")
            ],
            watched=entrant_watch.search_names(watched_entrants),
        )
        state_policy_task = fetch_state_policy_async(session)
        # Results dates, ex-dates and AGMs ahead, from NSE's own calendars.
        # Rotation has already run, so this is today's watchlist.
        from providers.nse_calendar import fetch_calendar

        calendar_task = asyncio.to_thread(
            fetch_calendar,
            [
                st.get("ticker")
                for sec, stocks in watchlist.items()
                if sec != "macro_indicators" and isinstance(stocks, list)
                for st in stocks
                if isinstance(st, dict) and st.get("ticker")
            ],
        )

        (
            pli_competitors,
            (agreements, launches),
            sebi_filings,
            inst_activity,
            corp_filings,
            _isin_added,
            global_market_news,
            state_policy,
            nse_calendar,
        ) = await asyncio.gather(
            pli_task,
            adv_rss_task,
            sebi_task,
            inst_task,
            filings_task,
            isin_refresh_task,
            global_events_task,
            state_policy_task,
            calendar_task,
        )

        from history.store import HistoryStore

        store = HistoryStore()

        merged_competitors = store.deduplicate_and_merge(
            "emerging_competitors", pli_competitors, ["name", "scheme"]
        )
        merged_agreements = store.deduplicate_and_merge(
            "corporate_agreements", agreements, ["company", "title"]
        )
        merged_launches = store.deduplicate_and_merge(
            "product_launches", launches, ["company", "product"]
        )
        merged_filings = store.deduplicate_and_merge(
            "corporate_filings", corp_filings, ["company", "filing"]
        )
        merged_sebi = store.deduplicate_and_merge(
            "sebi_filings", sebi_filings, ["company", "link"]
        )
        merged_inst = store.deduplicate_and_merge(
            "institutional_activity", inst_activity, ["company", "title"]
        )

        data["emerging_competitors"] = merged_competitors
        data["corporate_agreements"] = merged_agreements
        data["product_launches"] = merged_launches
        data["sebi_filings"] = merged_sebi
        data["institutional_activity"] = merged_inst
        data["corporate_filings"] = merged_filings
        # Room for the company searches: every anchor, partner and watched
        # entrant, eight to a search (scraper.company_queries).
        data["global_market_news"] = global_market_news[:80]
        # State policy accumulates like the other feeds, but only for as long
        # as the policy balance looks back: an older measure is already
        # history, and the reader has read it.
        from analysis.policy_impact import prune_state_policy

        data["state_policy"] = prune_state_policy(
            store.deduplicate_and_merge("state_policy", state_policy, ["title"])
        )

        # Market-event engine: classify WHAT happened across every collected
        # headline, keep a rolling window via the committed history, and let
        # the entity graph grow itself from tie-up headlines.
        from analysis.entity_graph import (
            apply_accepted_proposals,
            harvest_partner_edges,
            load_entity_graph,
            record_partner_proposals,
        )
        from analysis.event_engine import (
            annotate_event_materiality,
            classify_headlines,
            compute_supply_stress,
            refresh_merged_events,
        )

        graph = load_entity_graph()
        # Before classification: a partner accepted since the last run must
        # already be a known entity when today's headlines are read.
        apply_accepted_proposals(graph)
        from analysis.headline_text import is_filing_noise

        filings = data.get("corporate_filings") or []
        noise = sum(
            1
            for f in filings
            if isinstance(f, dict) and is_filing_noise(f.get("filing"))
        )
        log.info(
            f"Filings: {noise} of {len(filings)} are statutory housekeeping and "
            "are left out of event classification and the LLM reader."
        )
        events = classify_headlines(data, watchlist, graph)

        # Second reader. Optional: without GEMINI_API_KEY, or on any API
        # failure, it is skipped and the rules carry the run alone.
        from analysis.competitive_intel import (
            collect_dates,
            collect_headlines,
            collect_sources,
        )
        from analysis.llm_reader import read_headlines, reconcile

        readings, llm_status = read_headlines(collect_headlines(data, watchlist))
        reader_runtime.note(
            "events",
            {k: llm_status[k] for k in ("read", "cached", "pending")},
            llm_status["skipped"],
        )
        # The email reads gists from the cache file this just rewrote.
        from analysis.llm_reader import reset_cached_readings

        reset_cached_readings()
        events, llm_stats = reconcile(events, readings, watchlist, data, graph)
        if llm_status["skipped"]:
            log.info(
                f"LLM reader: skipped ({llm_status['skipped']}); "
                f"{llm_status['cached']} cached reading(s) used, "
                f"{llm_status['pending']} headline(s) unread."
            )
        else:
            log.info(
                f"LLM reader ({llm_status.get('model') or 'no model answered'}): "
                f"{llm_status['read']} new, {llm_status['cached']} "
                f"cached, {llm_status['pending']} left for later runs."
            )
        log.info(
            f"Reconciled: {llm_stats['corroborated']} corroborated, "
            f"{llm_stats['disagreed']} disputed, {llm_stats['llm_only']} LLM-only."
        )

        # Which way policy news cuts, per sector — the reader's policy fields.
        from analysis.policy_impact import (
            merge_repeat_policies,
            annotate_sector_news,
            policy_impacts,
            sector_policy_balance,
        )
        from config import SECTOR_METADATA as _SECTORS

        # One row per measure: outlets reporting the same one are merged
        # before the per-sector tally counts it.
        data["policy_impacts"] = merge_repeat_policies(
            policy_impacts(readings, collect_sources(data, watchlist))
        )
        data["policy_balance"] = sector_policy_balance(data["policy_impacts"])
        labelled = annotate_sector_news(data, readings, list(_SECTORS))
        log.info(
            f"Policy direction: {len(data['policy_impacts'])} policy headline(s) "
            f"with a sector effect; {len(data['policy_balance'])} sector(s) touched; "
            f"{labelled} sector feed item(s) labelled."
        )
        # Re-attribute the merged list with the current rules, so a fix to the
        # matcher reaches events carried over from earlier runs instead of
        # only applying to today's.
        data["market_events"] = refresh_merged_events(
            # Capped inside, after the stale events have gone.
            store.deduplicate_and_merge(
                "market_events", events, ["headline", "event_type"]
            ),
            watchlist,
            graph=graph,
            sources=collect_sources(data, watchlist),
        )
        annotate_event_materiality(data["market_events"], watchlist)

        # Governments' MoUs and pacts: no measure was taken, so the policy
        # reader lists none; they are tie-ups with a government party.
        from analysis.policy_impact import government_partnerships

        data["policy_partnerships"] = government_partnerships(data["market_events"])
        hard = sum(1 for r in data["policy_impacts"] if r.get("strength") == "hard")
        log.info(
            f"Policy strength: {hard} of {len(data['policy_impacts'])} measure(s) "
            "approved or in force; "
            f"{len(data['policy_partnerships'])} government partnership(s) "
            "(MoUs, pacts) in the last 30 days."
        )

        # How much to believe each event: how many outlets reported the
        # story, and whether the holding disclosed it to the exchange.
        from analysis.event_evidence import (
            cluster_stories,
            confirm_with_filings,
            prune_filings,
        )

        data["exchange_filings"] = prune_filings(
            store.deduplicate_and_merge(
                "exchange_filings",
                held_exchange_filings,
                ["ticker", "text", "date"],
            )
        )
        stories = cluster_stories(data["market_events"])
        confirmed = confirm_with_filings(
            data["market_events"], data["exchange_filings"]
        )
        log.info(
            f"Event evidence: {len(data['market_events'])} event(s) in {stories} "
            f"stor(ies); {confirmed} confirmed by an exchange filing "
            f"({len(data['exchange_filings'])} holding filings on record)."
        )
        data["supply_stress"] = compute_supply_stress(data["market_events"], graph)
        harvest_partner_edges(data["corporate_agreements"], watchlist, graph)
        # Tie-ups with someone we do NOT hold: queued for a person to review,
        # never written straight into the graph. See the function for why.
        # Headlines earlier thesis checks read as another company's news, or
        # as the holding's global group's (Siemens AG's partners are not
        # Siemens Ltd's), are left out; today's are taken back once today's
        # check has run.
        from analysis.thesis_check import group_headlines, namesake_headlines

        record_partner_proposals(
            data["market_events"],
            graph,
            namesakes=namesake_headlines() | group_headlines(),
        )

        # Second-order implications of events that name nobody we hold. Kept
        # deliberately downstream of attribution and deliberately OUT of
        # scoring, thesis health and the early-warning engine: those grade
        # evidence, and a read-through is a hypothesis with its reasoning
        # attached. See analysis/read_through.py for why that separation is
        # the whole point.
        from analysis.read_through import compute_read_throughs

        data["read_throughs"] = compute_read_throughs(
            data["market_events"],
            graph,
            watchlist,
            headlines=collect_headlines(data, watchlist),
            # Whose deals with a holding's partner read against the holding.
            peers=data.get("peer_competitors"),
            published=collect_dates(data, watchlist),
        )

        # The price-based counterpart of supply_stress above. That one counts
        # supply-side headlines, so a quarter where copper quietly rose 18%
        # with nobody writing about it produced no signal at all.
        from analysis.input_cost import compute_input_cost_shock

        data["input_cost_shock"] = compute_input_cost_shock()

    # Revenue growth first: it annotates each holding's TTM figure, which the
    # scoring model below reads. Running it afterwards left the scorer with no
    # growth input at all, silently.
    from analysis.sector_growth import build_sector_growth

    data["sector_growth"] = build_sector_growth(watchlist)

    # Compile margin of safety and moat analytics
    build_dashboard_views(data, watchlist)

    # Estimate-revision momentum: this run's targets/coverage vs the prior run
    data["estimate_revisions"] = revisions_mod.compute_revision_momentum(
        watchlist, prior_estimates
    )

    # Variant perception: where our independent Graham estimate diverges most
    # sharply from analyst consensus.
    data["variant_perception"] = compute_variant_perception(watchlist)

    # Sector S-curve stage, from trailing quarterly sales trends already fetched.
    data["curve_stage"] = classify_sector_curve_stage(watchlist)

    # Score any rotation decisions old enough to judge, and persist the ledger
    # so the hit-rate accumulates across runs.
    postmortem.score_pending_decisions(rotation_ledger, watchlist)
    data["rotation_hit_rate"] = postmortem.compute_hit_rate(rotation_ledger)
    data["rotation_recent_outcomes"] = postmortem.recent_outcomes(rotation_ledger)
    data["watchlist_changes"] = postmortem.recent_changes(rotation_ledger)
    # Every pick against the Nifty 50 (and its sector index) since the day it
    # was made — exits included, which the target-based post-mortem skips.
    from analysis.track_record import build_track_record

    data["track_record"] = build_track_record(rotation_ledger, watchlist)
    postmortem.save_ledger(rotation_ledger)

    # Sector-relative valuation: annotate stocks with peer-group P/E context
    from analysis.sector_valuation import build_sector_valuation

    data["sector_valuation"] = build_sector_valuation(watchlist)

    # Establish the historical-MF institutional accumulation baseline (backtesting)
    from analysis.backtesting import build_institutional_baseline

    data["institutional_baseline"] = build_institutional_baseline()

    # Synthesize a prioritized early-warning feed from the collected signals
    from analysis.early_warning import generate_early_warnings
    from analysis.competitive_intel import detect_new_entrants

    # Connect fetched headlines to the incumbents they threaten (e.g. Amber
    # Enterprises moving on mobile manufacturing = a Dixon problem) before
    # the early-warning engine runs.
    data["new_entrants"] = detect_new_entrants(data, watchlist)
    watched_entrants = entrant_watch.update_watched(
        watched_entrants, data["new_entrants"], registered_names
    )
    entrant_watch.save_watched(watched_entrants)
    if watched_entrants:
        log.info(
            f"Entrants watched: {len(watched_entrants)} — "
            + "; ".join(
                f"{w['name']}{' (' + w['ticker'] + ')' if w.get('ticker') else ''} "
                f"→ {w['sector']}, last flagged {w['last_seen']}"
                for w in watched_entrants
            )
        )

    # Tag each warning against the previous run so the dashboard can lead
    # with what is new rather than re-presenting yesterday's standing
    # conditions.
    from dashboard.payload import annotate_warning_status

    data["early_warnings"] = annotate_warning_status(
        generate_early_warnings(data, watchlist),
        prior.get("early_warnings") or [],
    )

    # Attribute collected headlines to the holdings they actually name, so
    # picking a company shows that company's coverage rather than its
    # sector's.
    from analysis.stock_topics import build_stock_topics

    data["stock_topics"] = build_stock_topics(data, watchlist)

    # The same attribution kept as a full audit — merged and excluded items
    # included — written per ticker so the browser pays for it only when a
    # reader opens a drawer. The counts ride in the payload; the detail does
    # not, which is what keeps dashboard_data.json a display copy.
    from analysis.coverage import build_coverage, coverage_counts
    from history.store import write_coverage_sidecars

    coverage = build_coverage(data, watchlist)
    data["coverage_count"] = coverage_counts(coverage)
    write_coverage_sidecars(coverage)
    # A holding its own news names only by ticker: its stored name is not how
    # headlines write it, and every headline without the ticker is lost.
    by_ticker_only = company_names.found_only_by_ticker(watchlist, coverage)
    if by_ticker_only:
        log.warning(
            "Names: found in their own news only by ticker, so the name is not "
            "how headlines write it (headline_names.json takes shorter forms): "
            + ", ".join(f"{t} '{n}' ({k} items)" for t, n, k in by_ticker_only)
        )

    # Thesis health: does the accumulated evidence this cycle still support
    # each holding's catalyst, or has a kill criterion tripped?
    data["thesis_health"] = compute_thesis_health(
        watchlist, data["early_warnings"], data["estimate_revisions"]
    )
    # Kept on each holding across runs: a holding no analyst covers is
    # replaced only after its thesis stays Broken (analysis/rotation.py).
    from analysis.rotation import HUGE_UPSET_RUNS
    from analysis.thesis import record_broken_runs
    from providers.yahoo import has_analyst_consensus

    broken_runs = record_broken_runs(watchlist, data["thesis_health"])
    uncovered = {
        s["ticker"]
        for sec, stocks in watchlist.items()
        if sec != "macro_indicators" and isinstance(stocks, list)
        for s in stocks
        if isinstance(s, dict) and s.get("ticker") and not has_analyst_consensus(s)
    }
    watched = {t: n for t, n in broken_runs.items() if t in uncovered}
    if watched:
        log.info(
            f"Thesis: Broken on consecutive runs, for holdings no analyst covers "
            f"(replaceable at {HUGE_UPSET_RUNS}): "
            + ", ".join(f"{t} {n}" for t, n in sorted(watched.items()))
        )

    # Thesis check: does any headline about a holding contradict the words of
    # its thesis? An LLM reading, shown beside the health status as a prompt
    # to review — it changes no status, score or warning.
    # Sector placement: holdings whose own industry does not fit the sector
    # they sit in. Reported, never moved — that is the owner's call.
    from analysis.sector_fit import audit_watchlist

    data["sector_fit"] = audit_watchlist(watchlist)
    fit = data["sector_fit"]
    log.info(
        f"Sector fit: {fit['checked']} holding(s) checked, "
        f"{len(fit['misfits'])} misfiled"
        + (
            " — "
            + "; ".join(
                f"{m['ticker']} ({m['industry']}) in {m['sector']}"
                + (f", fits {'/'.join(m['suggested'])}" if m["suggested"] else "")
                for m in fit["misfits"]
            )
            if fit["misfits"]
            else ""
        )
        + f"; {len(fit['unverified'])} without an industry on record."
    )

    from analysis.entity_graph import drop_namesake_proposals
    from analysis.thesis_check import (
        annotate_health,
        group_headlines,
        namesake_headlines,
        run_thesis_check,
    )

    data["thesis_check"] = run_thesis_check(watchlist, coverage)
    annotate_health(data["thesis_health"], data["thesis_check"])
    # Every AI reader has run: what each asked of which model, and what failed
    # (analysis/reader_runtime.py), for the log and the System view.
    thesis_status = data["thesis_check"].get("status") or {}
    reader_runtime.note(
        "thesis",
        {k: thesis_status.get(k) for k in ("read", "cached", "pending")},
        thesis_status.get("skipped") or "",
    )
    reader_runtime.note(
        "check",
        {
            "confirmed": thesis_status.get("confirmed"),
            "refused": thesis_status.get("refused"),
            "pending": thesis_status.get("checks_pending"),
        },
        thesis_status.get("checks_skipped") or "",
    )
    data["ai_readers"] = reader_runtime.report()
    log.info(f"AI readers: {reader_runtime.summary()}.")
    # Today's readings and every earlier run's: a day the check cannot run
    # must not put namesakes back on the Companies view or in the queue.
    namesakes = namesake_headlines(data["thesis_check"])
    group_news = group_headlines(data["thesis_check"])
    drop_namesake_proposals(namesakes | group_news)

    # One card per holding — its recent activity and the policies touching
    # its sector — for the dashboard's Companies view.
    from analysis.company_digest import build_company_digest

    data["company_digest"] = build_company_digest(
        watchlist,
        coverage,
        data,
        prices=weekly_closes,
        namesakes=namesakes,
        group_news=group_news,
    )

    # What is coming up for each holding, and what the results that came in
    # since the last run said (analysis/event_calendar.py).
    from analysis.event_calendar import build_calendar, update_results

    data["event_calendar"] = build_calendar(
        watchlist,
        fetched=nse_calendar,
        filings=data.get("exchange_filings"),
        prior=prior.get("event_calendar"),
    )
    cal = data["event_calendar"]
    log.info(
        f"Calendar: {len(cal['upcoming'])} event(s) in the next {cal['ahead_days']} "
        f"days for {len({e['ticker'] for e in cal['upcoming']})} holding(s), "
        f"{len(cal['next_results'])} with a results date; "
        f"{cal['sources']['filings']} from filings, "
        f"{cal['sources']['carried']} carried from the last run."
    )
    data["results"] = update_results(watchlist, prior.get("results"))

    # The book: positions in portfolios.json valued, measured against the
    # benchmark and checked against their limits, with the orders that would
    # restore the targets (analysis/portfolio.py).
    from analysis.portfolio import build_portfolios

    data["portfolio"] = build_portfolios(
        watchlist, weekly_closes, prior=prior.get("portfolio")
    )

    # What is new since the previous run, for the top of the dashboard and
    # the email (analysis/changes.py).
    from analysis.changes import build_changes

    data["changes"] = build_changes(
        data,
        prior,
        held_before=held_before,
        held_now={
            str(st.get("ticker")).upper()
            for sec, stocks in watchlist.items()
            if sec != "macro_indicators" and isinstance(stocks, list)
            for st in stocks
            if isinstance(st, dict) and st.get("ticker")
        },
    )
    log.info(
        "Since the last run: "
        + ", ".join(f"{n} {k}" for k, n in data["changes"]["counts"].items())
        + "."
    )
    digest = data["company_digest"]["companies"]
    log.info(
        f"Company digest: {len(digest)} holding(s); "
        f"{sum(1 for c in digest if c['activity_count'])} with activity and "
        f"{sum(1 for c in digest if c['policy_count'])} with a policy touching "
        f"them in the last {data['company_digest']['window_days']} days."
    )

    # Save watchlist changes
    save_watchlist(watchlist)

    # Save dashboard JSON
    save_data_for_dashboard(data, watchlist)

    # Build and send email. Subject, body and plain-text part all come from
    # one summary, so the inbox line cannot disagree with the briefing.
    message = build_briefing_email(data, watchlist)
    log.info(f"Briefing subject: {message['subject']}")
    send_email(message["html"], message["subject"], message["text"])

    # Deliberately after the send: a degraded briefing is still worth reading,
    # and it carries the evidence needed to diagnose the degradation. This only
    # decides whether the job reports success.
    from health import log_run_health

    healthy = log_run_health(data, watchlist)

    log.info("Briefing cycle finished successfully.")
    return healthy


if __name__ == "__main__":
    if not asyncio.run(run_pipeline()):
        sys.exit(1)
