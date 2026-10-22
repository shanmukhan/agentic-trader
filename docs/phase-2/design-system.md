# Phase 2 — light visual design system

Status: design contract 1.0, 22 October 2026 IST. These are proposed reusable tokens
and component rules; the shipped stylesheet is not rewritten during this phase.
Reference: `images/Agentic Trader Dashboard UI Collage.png`, interpreted as a visual
reference, not a source of account balances, recommendations or backtest results.

## Foundation tokens

Use a locally served system-font stack; no remote font, icon or chart dependency is
required for the shell. Product tokens have an `invest-` prefix to prevent collisions
with legacy pages. Consolidate existing overrides behind component tests during Phase 3.

| Token | Proposed value | Purpose |
|---|---|---|
| `--invest-background` | `#F5F7FA` | Neutral workspace canvas |
| `--invest-surface` | `#FFFFFF` | Opaque cards, dialogs and tables |
| `--invest-text` | `#172B3A` | Primary text and financial values |
| `--invest-muted` | `#5B6B7D` | Secondary text; never hide a material restriction |
| `--invest-caption` | `#607285` | Group labels and timestamps |
| `--invest-teal` | `#0F766E` | Primary task and selected navigation |
| `--invest-blue` | `#265D97` | Analytical secondary series and links |
| `--invest-selected-bg` | `#E7F3F0` | Selected navigation surface |
| `--invest-selected-text` | `#09665C` | Selected navigation text |
| `--invest-positive` | `#13754C` | Explicit gain or successful named state |
| `--invest-negative` | `#B42332` | Explicit loss, destructive action or error |
| `--invest-warning` | `#895300` | Missing/stale/review-required warning text |
| `--invest-warning-bg` | `#FFF7DF` | Light warning surface |
| `--invest-divider` | `#E1E7EE` | Nonessential row separators |
| `--invest-input-border` | `#81909F` | Essential control boundary |
| `--invest-focus` | `#087F8C` | Visible keyboard focus |

Normal text must achieve at least 4.5:1 contrast; large text and essential nontext
controls at least 3:1. Validate actual foreground/background pairings, including
selected, warning, dialog, chart/table and error states. Disabled controls are clearly
disabled and explained when necessary; do not use low opacity for essential warnings.
Documented token checks are not a claim of full WCAG conformance in a rendered app.

Never encode meaning by color alone. Label Gain/Loss, Buy/Sell, Connected/Disconnected,
Stale/Current and Partial/Complete. Use teal/blue for navigation and analysis; reserve
red/green for meaningful direction/status. Do not color every metric or candidate rank.

## Typography and spacing

- Font: `system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif`.
- Body 16px/1.5, form/table labels 14px/1.5, captions at least 12px/1.5. No tiny
  disclaimer wall. Headings: 28/36px page, 20/28px section, 16/24px component.
- Weights 400 normal, 600 labelled emphasis, 700 headings/critical amounts. Metric
  amounts approximately 28px/36px with tabular figures; allow long exact values to wrap.
- Space scale 4, 8, 12, 16, 24, 32, 48px. Page gutters 16px mobile, 24–32px desktop;
  card padding 20–24px; main section gap 24px; field/control gap 8–12px.
- Surfaces: 10–12px radius, 1px neutral separator; restrained shadow only for elevation
  or a dialog. Avoid nested card walls, ornamental gradients or fake sparklines.
- Controls: at least 44px effective touch target, primary action clearly labelled,
  one primary per task group. Use native inputs/buttons/selects and semantic labels.
- Financial decimals remain exact. Display rounding, when allowed by a metric contract,
  is explicitly a presentation format and never changes admission/accounting inputs.

## Responsive composition

| Width | Navigation | Content behavior |
|---|---|---|
| 320–767px | Native menu/disclosure with labelled current destination; all screens and Help reachable | One metric/card column by default; stack controls, readable row details; dialog fits viewport/keyboard |
| 768–1023px | Collapsible grouped sidebar | Two metric columns where labels fit; chart and evidence stack |
| 1024px and above | Approximately 232px grouped sidebar | Four primary metrics where content fits; chart/evidence about 3:1; bounded content max-width |

Use content fit, not breakpoint alone, to avoid overflow. At 200% zoom, components
reflow instead of clipping or shrinking text. Essential tables may scroll horizontally
inside a labelled region, with a mobile row-detail alternative and reachable actions.
Do not crop exact money, hide warnings or make a hover tooltip the only source of data.
Native page scroll is primary; large evidence/log sections may have labelled bounded
scroll. The current frame-height safety limit retains a scroll fallback, not hidden
content. Modal positioning follows the visible frame/parent intersection.

## Component inventory for Phase 3

| Component ID | Variants/states | Required contract |
|---|---|---|
| `INV-SHELL` | Locked/unlocked; grouped/collapsed/mobile | In-memory authorization, stable aliases/history, paper-only, pending-action navigation guard |
| `INV-METRIC` | Available/partial/unavailable; current/stale/unknown freshness | Definition, exact value/null, unit, dates, reason and source; no null→0 fallback |
| `INV-STATUS` | Connection, quote, session, strategy, action | Named independent state; text/icon plus color, not a single green readiness dot |
| `INV-NEXT-ACTION` | Setup/review/wait/recover/none | One direct safe action and why; navigation is not approval |
| `INV-TABLE` | Read-only/selectable; empty/loading/paged/error | Semantic headers/caption, exact amounts, scoped result count, keyboard/touch row details |
| `INV-EXPLANATION` | Positive/contradictory/missing/risk | Tied to actual calculation/source; no profit probability from rank |
| `INV-CHART` | History/indicators/allocation; empty/partial/stale/error | Source/basis/time/units, noncolor distinctions, exact table and no fake data |
| `INV-DIALOG` | Review, activation, connection, financial confirmation | Visible before focus, server binding, cancel/lock cleanup, one-shot submit, unknown-outcome recovery |
| `INV-ASYNC-FORM` | Idle/pending/succeeded/rejected/unknown | Inline status, preserve edits, suppress duplicate actions, no silent write retry |
| `INV-JOB` | Queued/running/cancel_requested/completed/cancelled/interrupted/failed | Honest progress scope, immutable inputs, bounded isolated work, incomplete results withheld |
| `INV-DISCLOSURE` | Summary/evidence/technical detail | Native keyboard controls; material consequences remain visible without expansion |
| `INV-TERM-HELP` | Tooltip/popover/lesson link | Focus/touch reachable, Escape dismiss, plain language; essential facts visible inline |

Use one shared helper for confirmation placement/lifecycle across all existing
controllers. Put reusable read-state/formatting/presentation utilities outside financial
admission logic. A component must not call an order API as a side effect of rendering,
selecting a tab or dismissing a dialog. No frontend component owns the true risk gate.

## Motion, focus and accessible content

Honor reduced motion; no flashing prices or looping attention effects. Loading uses
plain text/status; an indeterminate indicator does not claim a completion percentage.
Keep native tab order and visible focus, skip links, landmarks and clear headings.
Changing a route focuses the page/target after it exists; polling does not steal focus.
A dialog captures focus natively and restores the initiating control on cancellation.
Use polite live regions for meaningful state changes, not every tick or chart hover.

Provide text equivalents for allocation and chart data. A chart library's canvas or
SVG alone is insufficient. Definitions must explain bid/ask, costs held, net unrealized
P&L, daily P&L baseline, claim valuation, drawdown and backtest limitations. Learning
Center content is educational; no design example is a personal investment instruction.

## Design review artifact and limits

[prototype.html](prototype.html) is an offline navigation/state/dialog review. It uses
local template descriptions and unavailable values; it is not a deployed replacement,
real account snapshot or indicator/backtest implementation. The prototype has no fetch,
WebSocket, storage, credential field or financial submission. Its rendering still needs
browser review; source/interaction/contrast checks alone do not establish device acceptance.
See [acceptance-plan.md](acceptance-plan.md) for specific release gates.
