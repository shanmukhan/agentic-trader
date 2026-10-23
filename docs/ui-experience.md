# Workspace usability and icons — 0.19.0

The 23 October 2026 usability pass makes the existing paper workflows easier to scan.
It adds a local SVG icon system, shorter repeated status messages, progressive help
and a four-step investment-policy draft form. It does not change account values,
quote freshness, risk checks, broker credentials, trading authority or confirmation
requirements. A saved policy draft still cannot be activated or executed.

## Open the updated interface

From the repository directory, run:

```sh
./scripts/start_ui.sh
```

If an older server owns the account, stop it gracefully in its owning terminal first.
The launcher checks the application version; it does not silently replace that process.
Open the launcher's `/workspace` address, normally `http://127.0.0.1:8004/workspace`,
then unlock with `TRADING_OPERATOR_TOKEN` from the private local `.env`.
Zerodha request/access tokens are not workspace passwords. Reloading clears the
in-memory unlock token and requires unlocking again.

## Navigation, state and help

All twelve sidebar destinations have a consistent icon beside their existing text
label. Refresh, access and selected section headings use the same local SVG sprite.
Icons are decorative and hidden from assistive technology; visible text supplies
the meaning. There are no icon-only financial actions or external font/icon services.
An unavailable icon therefore cannot remove an action's label or change its result.

The compact workspace header retains the current destination, paper-only identity,
lock state and **Lock workspace** control. At narrow widths, use **Menu · current
screen** to reach the grouped destinations. Controls keep visible focus and touch
targets; selection remains available through text and `aria-current`, not color alone.

When setup is incomplete, its current next step stays visible. Expand the setup
note for its action link, reason and longer guidance; it starts collapsed after unlocking. This is
a link to an existing reviewed workflow, not an approval or a connection request.
The Learning Center's setup checklist remains available for the full sequence.

Dashboard and other saved views keep their observation timestamp and stale-display
state. Successful refresh feedback is shorter. A saved view still requires refresh
to inspect current quote, valuation and operating evidence; a connected socket alone
does not prove a usable execution quote. Errors, unknown outcomes and blocked actions
continue to explain their recovery steps.

## Portfolio and Stock Analysis

Portfolio keeps valuation coverage and quote limitations visible beside exact saved
figures. Expand its valuation definitions for the accounting scope and formulas.
Collapsing that explanation does not change the denominator, cash reservations,
fee estimates, claims, holdings or unavailable metrics. Financial values retain the
server's exact decimal strings. Wide evidence tables scroll inside labelled,
keyboard-focusable regions rather than forcing the whole page sideways.

In Stock Analysis, select a saved stock, interval and display range, then inspect
its quote state separately from the chart. Expand chart help and the legend when
you need the source/display explanation. The display range still changes only the
drawing and table, without fetching history or resetting indicator seeds. Chart
coordinates remain approximations; the indicator and candle tables retain exact
values. Warmup, stale quotes and missing source evidence remain explicit.

Backtest histories are individually expandable and retain exact values in bounded
scroll regions. Job cards use the registered bundle name and keep the full identifier
in **Job identity**. Risk Management separates **Emergency actions** from **Entry
permissions** while retaining the same review and confirmation controls.

## Investment-policy draft steps

Open **Strategies → Create or inspect investment policy drafts**. The existing four
parameter groups are presented as steps, with progress and Previous group/Next group navigation.
Every financial choice still begins blank. Moving between steps does not save,
preview, select defaults, install a calendar or change a policy. You can retain an
incomplete draft; complete the fields you intend to specify before reviewing it.

Unit/cadence help follows your explicit selections. Invalid fields are linked to
their error messages so you can identify and focus the affected input. Correct the
input and preview again; failed validation does not save a snapshot. **Review all choices**
still obtains the exact server preview, and saving still requires the existing
confirmation and acknowledgement. **Edit a copy** preserves the original snapshot.

Unsaved edits, pending requests and uncertain saves keep their existing navigation
guards. For an unknown save outcome, refresh saved snapshots and reconcile before an
explicitly reviewed same-content retry. There is no automatic save or POST retry.
Lock clears private in-memory edits and displayed evidence; it does not cancel an
already accepted server action, disconnect the feed, disarm automation or sell holdings.
See [the full draft schema and recovery contract](investment-policy-drafts.md).

## Recovery and acceptance limits

If the updated layout or icons do not appear, verify that the owning server is the
current version, then reload the whole workspace and unlock again. If a confirmation
cannot be displayed, no new action is submitted: reopen the relevant screen and
review again. Cancel/Escape retains its existing meaning. Confirmations remain native
dialogs positioned in the visible parent viewport, including long embedded screens.

The icon asset is served from the same application origin as the page. No broker,
credential or account API is added by this usability pass. Backtest launching remains
gated by verified OS isolation and is unavailable on the implementation Mac; investment
execution, rebalancing and full Phase 5 acceptance remain unfinished.

Automated controller/accessibility checks and any disposable rendered checks are
recorded in [the validation plan](test-plan.md). Simulated DOM evidence does not prove
browser layout, mobile/touch, zoom, broker or device acceptance. No test of this change
should operate the user's actual account or convert synthetic evidence into a
real-market claim.
