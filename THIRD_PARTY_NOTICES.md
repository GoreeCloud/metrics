# Third-party components and provenance

The hub, agent, web screens, and native client logic are newly authored for GoreeCloud. Beszel is an architectural reference only; its source code has not been copied.

| Technology | Role | Upstream | License |
| --- | --- | --- | --- |
| Beszel | Design reference only | https://github.com/henrygd/beszel | MIT |
| FastAPI | Web API | https://github.com/fastapi/fastapi | MIT |
| Uvicorn | ASGI server | https://github.com/encode/uvicorn | BSD-3-Clause |
| psutil | Host metrics | https://github.com/giampaolo/psutil | BSD-3-Clause |
| React | Web components | https://github.com/facebook/react | MIT |
| Vite | Frontend build | https://github.com/vitejs/vite | MIT |
| Recharts | Time-series chart | https://github.com/recharts/recharts | MIT |
| lucide-react | Interface iconography | https://github.com/lucide-icons/lucide | ISC |
| Flutter / Dart | Native Linux and Android | https://github.com/flutter/flutter | BSD-3-Clause |
| Dart http | Native HTTP client | https://github.com/dart-lang/http | BSD-3-Clause |
| GoreeCloud UI | Internal design token reference | https://github.com/GoreeCloud/gc-ui | MIT |

Expected upstream license identities are provided for auditing; review resolved transitive dependencies and distribution obligations before a release. Flutter-generated platform runners and external package downloads retain their respective upstream rights. No upstream Beszel code is redistributed here.

The native Flutter source snapshot at apps/native/design/gc.tokens.json is MIT-licensed GoreeCloud UI alpha-token data, pinned to upstream commit be8b819748d1ef0f6b2d3e786f4b22864cb3d07d. It is generated into Dart constants and has not been accepted as a final public design standard.
