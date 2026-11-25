# Browser time-window controls

The Metrics React overview supports three owner-selectable historical time windows: six hours, 24 hours (default), and seven days. Switching the interval requests the selected host's existing authenticated history endpoint with a 400-point cap. The full selected window contributes to 400 or fewer time-bucket averages; the browser does not fetch raw unbounded samples.

The selector is keyboard-operable native buttons grouped with an accessible label, identifies the active period with aria-pressed, and reuses the current GoreeCloud UI semantic focus, surface, text, spacing and brand colors. It does not persist the owner token or history selection to localStorage. When the host or interval changes, the previous chart is cleared before the new result arrives; stale inflight requests are ignored by the effect cleanup.

These are chart averages, not per-second peak data; the latest system sample continues to provide current utilization. The period buttons are development-preview source controls. Targeted source/contract tests and the React TypeScript/Vite build are automated; real browser, mobile assistive technology, and founder visual acceptance remain pending. No production server or personal device was changed.
