# Deferred host-history visualization

The Recharts renderer is split into a dynamically imported React component, loaded only after an authenticated owner has selected a host with historical samples. It is not part of the initial login or empty-dashboard JavaScript entry bundle. The existing three-series CPU, memory and disk chart, axes, tooltip, hour interval, accessible label and GoreeCloud UI monitoring styles are preserved. A semantic loading status reserves the same chart height while the browser loads the optional component.

The component receives only bounded aggregate chart samples and a selected period—no bearer credential or HTTP client. The existing hub's full-window history endpoint still limits responses to 400 points in the web interface, and session-isolation checks prevent stale responses from restoring data after sign-out.

The source contract tests verify lazy loading, the preserved series and absence of credential handling in the visualization module; TypeScript/Vite production builds verify the separated chunk. End-to-end web browser performance and assistive-technology checks remain preview acceptance work. No deployed CDN or external third-party script was added.

Local reproducible build observation (Flutter unaffected): at source revision in this branch, Vite reported 245.19 kB initial JS and 435.32 kB deferred chart JS (before gzip), versus approximately 680.69 kB initial JS before extraction. This is a source/build measure, **not** a real browser load-speed benchmark; network transfer sizes after gzip were approximately 76.89 kB and 124.40 kB respectively.
