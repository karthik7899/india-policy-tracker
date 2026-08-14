/**
 * Headless smoke test for the dashboard, run against the committed dataset.
 *
 * The Python suite covers everything that produces a number. This covers the
 * layer that renders one, which pytest cannot reach: that every nav tab
 * actually activates, that nothing overflows horizontally on a phone, that no
 * page errors fire, and — the rule that is easiest to break by accident — that
 * opening the page fetches neither the per-ticker sidecars nor the full
 * corpus.
 *
 * Usage (from the repo root):
 *   python3 -m http.server 8899 --bind 127.0.0.1 &
 *   node scripts/smoke_dashboard.js
 *
 * Exits non-zero on any failure so it can gate a commit.
 */

// Playwright is usually a global install, which Node does not resolve from a
// project directory. Falling back to the global root keeps this runnable from
// the repo root without adding a dependency the pipeline itself never needs.
function loadChromium() {
    for (const id of ["playwright", "/opt/node22/lib/node_modules/playwright"]) {
        try {
            return require(id).chromium;
        } catch (e) {
            if (e.code !== "MODULE_NOT_FOUND") throw e;
        }
    }
    console.error(
        "playwright not found. Install it, or point NODE_PATH at the global\n" +
        "module root (e.g. NODE_PATH=$(npm root -g) node scripts/smoke_dashboard.js)."
    );
    process.exit(2);
}

const chromium = loadChromium();

const BASE = process.env.SMOKE_URL || "http://127.0.0.1:8899/index.html";

const TABS = [
    "dashboard", "holdings", "sectors", "agreements", "launches", "filings",
    "institutional", "research", "stocks", "valuation", "scoring", "graham",
    "buffett", "earlywarning", "caution", "system",
];

// Requests the sandbox proxy refuses. They are not page defects, and treating
// them as failures would make the check cry wolf on every run.
const PROXY_NOISE =
    /jsdelivr|fonts\.google|favicon|ERR_TUNNEL_CONNECTION_FAILED|ERR_CONNECTION_RESET|404 \(File not found\)/;

const VIEWPORTS = [
    { width: 1440, height: 900, colorScheme: "light", name: "1440 light" },
    { width: 390, height: 844, colorScheme: "dark", name: "390 dark" },
];

async function checkViewport(browser, vp) {
    const failures = [];
    const context = await browser.newContext({
        viewport: { width: vp.width, height: vp.height },
        colorScheme: vp.colorScheme,
    });
    const page = await context.newPage();

    page.on("pageerror", e => failures.push(`page error: ${e.message}`));
    page.on("console", m => {
        if (m.type() === "error" && !PROXY_NOISE.test(m.text())) {
            failures.push(`console error: ${m.text()}`);
        }
    });

    await page.goto(BASE, { waitUntil: "networkidle" });
    await page.waitForTimeout(1800);

    // The payload/corpus split. A renderer that reaches for a sidecar during
    // its first paint undoes the whole reason the split exists.
    const eager = await page.evaluate(() => ({
        sidecars: performance.getEntriesByType("resource")
            .filter(r => r.name.includes("/news/")).length,
        corpus: performance.getEntriesByType("resource")
            .filter(r => r.name.includes("history.json")).length,
    }));
    if (eager.sidecars) failures.push(`${eager.sidecars} sidecar(s) fetched on page load`);
    if (eager.corpus) failures.push("full corpus fetched on page load");

    for (const tab of TABS) {
        await page.evaluate(t => {
            const btn = [...document.querySelectorAll("[data-tab]")]
                .find(e => e.dataset.tab === t);
            if (btn) btn.click();
        }, tab);
        await page.waitForTimeout(220);

        const state = await page.evaluate(t => ({
            active: !!document.querySelector(`#tab-${t}.active`),
            overflow: document.documentElement.scrollWidth >
                document.documentElement.clientWidth,
            // Read defensively: a missing host must be reported as the
            // regression it is, not thrown as a TypeError that takes the
            // whole check down before it can say anything.
            crumb: ((document.getElementById("breadcrumb-bar") || {})
                .textContent || "").trim().length > 0,
        }), tab);

        if (!state.active) failures.push(`${tab}: pane did not activate`);
        if (state.overflow) failures.push(`${tab}: horizontal overflow`);
        if (!state.crumb) failures.push(`${tab}: breadcrumb empty`);
    }

    await context.close();
    return failures;
}

(async () => {
    let browser;
    let failed = 0;
    try {
        browser = await chromium.launch({
            executablePath: process.env.CHROMIUM_PATH || "/opt/pw-browsers/chromium",
        });

        for (const vp of VIEWPORTS) {
            const failures = await checkViewport(browser, vp);
            if (failures.length) {
                failed += failures.length;
                console.log(`FAIL ${vp.name}`);
                failures.forEach(f => console.log(`   ${f}`));
            } else {
                console.log(`ok   ${vp.name} — ${TABS.length} tabs, no overflow, no page errors`);
            }
        }
    } catch (e) {
        // An unhandled rejection here would exit 0 on some Node versions and
        // print a stack trace that reads nothing like a test result. A checker
        // that can crash silently is worse than no checker.
        console.log(`FAIL smoke test crashed: ${e && e.message}`);
        failed += 1;
    } finally {
        if (browser) await browser.close().catch(() => {});
    }
    process.exit(failed ? 1 : 0);
})();
