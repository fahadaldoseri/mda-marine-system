# Valuation

Playbooks for answering "what is this company worth": intrinsic (DCF), market-based (trading comps, precedent transactions), segment-based (SOTP), and share-count mechanics. Always load `formats/excel_standards.md` and `formats/metric_disambiguation.md` alongside this file when producing Excel output.

> The sole authoritative source for cross-module valuation discipline (primary-method declaration, cross-checks, bear/base/bull three-scenario framework, sensitivity analyses and parameter constraints) is [`references/metric-dictionary.md §General Valuation Discipline`](../../../metric-dictionary.md#general-valuation-discipline); this Playbook only supplements engineering steps and default values for specific models and does not redefine that discipline.

## Contents

| Task | File | Use when |
|---|---|---|
| DCF Model | [`dcf-model.md`](dcf-model.md) | Building a standalone discounted cash flow valuation for a company |
| Public Comps | [`public-comps.md`](public-comps.md) | Valuing a company using current market pricing of publicly traded peers |
| Precedent Transactions | [`precedent-transactions.md`](precedent-transactions.md) | Valuing a target using actual M&A transaction multiples paid by acquirers |
| SOTP Valuation | [`sotp-valuation.md`](sotp-valuation.md) | A multi-segment company requires segment-level valuation with distinct growth, margin, or risk profiles |
| Fully Diluted Share Count | [`fully-diluted-share-count.md`](fully-diluted-share-count.md) | Calculating fully diluted shares outstanding (FDSO) for use in market cap, per-share value, EPS, or valuation inputs
