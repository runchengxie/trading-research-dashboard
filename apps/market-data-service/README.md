# Market Data Service

Provider-neutral contracts and service-core primitives for live market data.

This first stage deliberately does not fetch from external providers or expose a
network API. It defines the stable boundary that later collector, Redis,
FastAPI, and WebSocket implementations can use:

- normalized A-share symbols such as `sz300246`;
- timezone-aware `Quote` values with source and status metadata;
- explicit current, stale, and unknown freshness states;
- environment-backed service configuration;
- an async `MarketDataProvider` protocol for replaceable providers.

Static Dashboard snapshots remain the production fallback until a later stage
adds the collector and API layers.
