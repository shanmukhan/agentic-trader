# Mobile UX Improvement Plan

> **Status:** Completed · All phases implemented (v1.1.2 Phases 1–3, v1.1.3 Phase 4)  
> **App version at plan creation:** Android 1.1.1 (code 12)  
> **App version after completion:** Android 1.1.3 (code 14)  
> **Scope:** Android app only — no financial logic, security model, or backend API changes

---

## Executive Summary

The app works correctly but requires domain knowledge to operate. A new user confronts
cryptic labels ("operator token", "Paper trading", "Manual mode"), no onboarding flow,
raw JSON detail trees on every screen, and status text that is hard to read at a glance.
This plan fixes that across four implementation phases, ordered by impact.

---

## Pain Points (per screen)

### Unlock / Pairing screen
| Issue | Severity |
|---|---|
| "Server operator token" label — user has no idea what this is or where to find it | 🔴 Critical |
| No explanation of what pairing means or why biometric is needed | 🔴 Critical |
| Pasting a long token is error-prone; no character counter | 🟡 Medium |
| Error banner gone on submit; user can't edit without re-typing | 🟡 Medium (fixed in 1.1.1) |

### Home screen (Overview)
| Issue | Severity |
|---|---|
| "Your paper account" section header is jargon | 🟡 Medium |
| Stale valuation hint is long and technical | 🟡 Medium |
| "Checked 21 Nov, 2:03 PM IST" — too many details upfront | 🟢 Low |
| DailyJourneyCard lacks any welcome text for a first-time user | 🔴 Critical |

### Daily Journey card (Step 1–4)
| Issue | Severity |
|---|---|
| Step label "Access" means nothing without context | 🟡 Medium |
| Step 0: "Kite access" — user might not know what Kite is | 🟡 Medium |
| Step 1: "Nifty 50 source and completed-history evidence is needed" — engineering speak | 🔴 Critical |
| Step 2: "One review covers strategy, stocks, exchange sessions…" — overwhelming | 🟡 Medium |
| Step 3: Text-only guidance for "choose a mode" with no explanation of implications | 🟡 Medium |
| "Setup details & completed checks" toggle is buried | 🟢 Low |

### Paper trading screen
| Issue | Severity |
|---|---|
| "Your trading mode · Current: manual. Feed connection alone cannot authorize trading." — dense | 🟡 Medium |
| Three mode buttons (Manual/Approval/Automatic) with no clear first-time recommendation | 🔴 Critical |
| Decisions section: raw JSON-like label "BUY · NSE:RELIANCE · awaiting_approval" | 🟡 Medium |
| Empty state "No strategy proposals yet" — no clear call to action | 🟡 Medium |

### Watchlist screen
| Issue | Severity |
|---|---|
| "Permitted NSE stocks" — not plain language | 🟡 Medium |
| "5 entry slots used today" — slot concept unexplained | 🟡 Medium |
| Account safety numbers shown without context | 🟢 Low |
| Search and add flow is two separate actions (search, then add) | 🟢 Low |

### Portfolio screen
| Issue | Severity |
|---|---|
| "Remaining basis" and "Estimated P&L" — financial jargon | 🟡 Medium |
| "An accepted order appears here only after actual simulated fills" — confusing | 🟡 Medium |

### Broker & data screen
| Issue | Severity |
|---|---|
| Mixed content: connection status + session + credentials + basket + calendar all on one page | 🔴 Critical |
| "Fallback: exchange a one-time request token" — too technical to understand | 🟡 Medium |
| Connection failed message is actionable but wordy | 🟢 Low |

### More / navigation
| Issue | Severity |
|---|---|
| "More" contains 11 items in two flat lists — no grouping or descriptions | 🟡 Medium |
| Page titles like "Discover stocks", "Your strategy", "Investment policies" have no subtitles | 🟢 Low |
| Bottom nav: "Paper" label is cryptic; "More" shows nothing about what's inside | 🟡 Medium |

### Settings & Security screens
| Issue | Severity |
|---|---|
| Settings is information-only (no interactive preferences except alerts) | 🟢 Low |
| Security screen: "Owner token · emergency device management" buried | 🟢 Low |

### Learning center
| Issue | Severity |
|---|---|
| Plain list of text topics — no visual hierarchy | 🟢 Low |
| Searchable but no categories | 🟢 Low |

---

## Implementation Phases

### Phase 1 — First impressions (highest impact, lowest risk)
*Target: a new user can pair, understand the app purpose, and reach the first step without asking for help.*

| ID | Change | File(s) | Notes |
|---|---|---|---|
| **P1-A** | Pairing screen: replace "Server operator token" with friendly explanation panel (what it is, where to get it, example length) | `MainActivity.kt` | No API change |
| **P1-B** | Pairing screen: add character count badge next to field | `MainActivity.kt` | Show e.g. "42 chars ✓ / need 32+" |
| **P1-C** | Home screen welcome banner for first-time users (before first unlock data loads) | `Branding.kt` | Show only when no data yet |
| **P1-D** | Daily Journey: replace step labels "Access / Data / Review / Trade" with plain-language subtitles inside the step card body | `DailyJourney.kt` | Don't change the circle labels, add body subtitles |
| **P1-E** | Daily Journey step 1 message: rewrite "source and completed-history evidence" → plain language | `DailyJourney.kt` | String change only |
| **P1-F** | Bottom nav: rename "Paper" → "Trading" and "More" → "Tools" | `MainActivity.kt` | Low risk label rename |

### Phase 2 — Mode & trading clarity
*Target: a user can select a trading mode confidently and understand what proposals mean.*

| ID | Change | File(s) | Notes |
|---|---|---|---|
| **P2-A** | Paper trading screen: add one-line mode descriptions next to each mode button | `Screens.kt` | Small label beneath each `Action` |
| **P2-B** | Paper trading screen: highlight the recommended mode (Approval) with a chip/badge | `Screens.kt` | Visual, no logic change |
| **P2-C** | Decision cards: use plain English header "Buy proposal: RELIANCE" instead of "BUY · NSE:RELIANCE · awaiting_approval" | `Screens.kt` | Strip `NSE:` prefix, friendly state |
| **P2-D** | Decision empty state: add a clear call-to-action link to Daily Journey | `Screens.kt` | `Action` button to `Page.HOME` |
| **P2-E** | "Your trading mode" section: add a one-sentence plain summary at the top | `Screens.kt` | Derived from `friendly(mode)` |
| **P2-F** | Mode help dialog: improve title and confirmation copy | `TradeGuidance.kt` | String changes only |

### Phase 3 — Navigation & information architecture
*Target: user can find any feature within two taps from Home.*

| ID | Change | File(s) | Notes |
|---|---|---|---|
| **P3-A** | "More" (Tools) screen: add one-line subtitles for each item | `Screens.kt` | Describe what each page does |
| **P3-B** | Broker & data screen: split into logical groups with clear section headers ("Market data", "Zerodha sign-in", "Stock universe", "Session calendar") | `ControlScreens.kt` | Re-order existing sections |
| **P3-C** | Watchlist: rename "Permitted NSE stocks" → "Your approved stocks" and explain "entry slots" in plain language | `WatchlistScreen.kt` | String changes |
| **P3-D** | Portfolio: rename "Remaining basis" → "Cost basis" and add tooltip-style caption | `PortfolioScreens.kt` | String changes |
| **P3-E** | Home screen: rename "Your paper account" → "Your virtual account" | `Screens.kt` | String change |
| **P3-F** | Daily Journey step descriptions: rewrite all four step body texts for plain language | `DailyJourney.kt` | Extend P1-D/E to all steps |

### Phase 4 — Polish & progressive disclosure
*Target: advanced users get more detail on demand; beginners see clean primary flows.*

| ID | Change | File(s) | Notes |
|---|---|---|---|
| **P4-A** | Learning center: add category chips (Setup, Trading, Safety, Research) | `ControlScreens.kt` | Filter by category |
| **P4-B** | Settings screen: add "How this app works" info card linking to Learn | `ControlScreens.kt` | Navigation shortcut |
| **P4-C** | Stale data hint: shorter, plain message ("Prices not updated — tap Refresh") | `Screens.kt`, `WatchlistScreen.kt` | Reduce hint verbosity |
| **P4-D** | Error messages: map common server errors to plain-language equivalents | `MainActivity.kt` | Small lookup map |
| **P4-E** | "Advanced" sections: consistently label as "Advanced (optional)" to reduce intimidation | Multiple files | Terminology pass |
| **P4-F** | Discovery screen: add subtitle "Research saved stocks" | `Screens.kt` | Section header hint |

---

## Implementation Order

```
Phase 1 (P1-A → P1-F)   → build, install on Samsung → commit v1.1.2
Phase 2 (P2-A → P2-F)   → build, install on Samsung → commit v1.1.3
Phase 3 (P3-A → P3-F)   → build, install on Samsung → commit v1.1.4
Phase 4 (P4-A → P4-F)   → build, install on Samsung → commit v1.1.5
```

---

## Success Metrics

| Metric | Before | Target |
|---|---|---|
| Steps to reach first meaningful action from first launch | 6+ | ≤ 3 |
| Number of technical/jargon terms visible on first unlock | 8+ | ≤ 2 |
| Pairing screen: user can self-answer "what is operator token?" | ❌ | ✅ with inline help |
| Trading mode: user can describe the difference between Approval and Automatic | ❌ | ✅ with inline labels |
| Any screen requires a support document to navigate | Several | None |

---

## Boundaries (Must Not Cross)

- ❌ Do not change financial logic, risk limits, or safeguard thresholds
- ❌ Do not remove or weaken any review/acknowledge dialog
- ❌ Do not change backend API contracts or the security model
- ❌ Do not add live-trading features or hint that real money is used
- ❌ Do not change the biometric auth or pairing flow's security behavior
- ✅ String/label changes are safe — they touch no logic
- ✅ Adding a `Text` or `Hint` composable below an existing one is safe
- ✅ Re-ordering or grouping sections within a screen is safe if no code path changes

---

## Files Changed Per Phase

| Phase | Kotlin files | Expected lines changed |
|---|---|---|
| 1 | `MainActivity.kt`, `DailyJourney.kt`, `Branding.kt` | ~40 |
| 2 | `Screens.kt`, `TradeGuidance.kt` | ~35 |
| 3 | `Screens.kt`, `ControlScreens.kt`, `WatchlistScreen.kt`, `PortfolioScreens.kt` | ~30 |
| 4 | `ControlScreens.kt`, `Screens.kt`, `WatchlistScreen.kt`, `MainActivity.kt` | ~25 |

---

## Appendix: Terminology Replacement Table

| Old term | New term | Where |
|---|---|---|
| Server operator token | Access passphrase / Your server passphrase | Pairing screen |
| Paper account / Paper trading | Virtual account / Simulated trading | Home, bottom nav |
| Paper (bottom nav) | Trading | Bottom nav |
| More (bottom nav) | Tools | Bottom nav |
| Manual mode | Paused / No auto-trading | Trading screen |
| Approval mode | Review-each-trade | Trading screen |
| Automatic mode | Auto-trade | Trading screen |
| Permitted NSE stocks | Approved stocks | Watchlist |
| Remaining basis | Original cost | Portfolio |
| Nifty 50 source and completed-history evidence | Today's stock data | Daily Journey |
| Feed connected / disconnected | Live prices on / off | Broker screen |
| Entry slots | Trade opportunities today | Watchlist |
| Kite session verified | Zerodha login OK | Daily Journey |
