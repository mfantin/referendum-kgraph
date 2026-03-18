# Italian Referendum Knowledge Graph - Live Prediction

Real-time knowledge graph and prediction tool for the Italian Constitutional Referendum on Justice Reform (Nordio Reform), March 22-23, 2026.

## Features

- **Live Knowledge Graph** with parties, politicians, polls, news articles, and sentiment signals
- **Real-time prediction** aggregating 4 weighted signals: polls, party strength, media sentiment, momentum
- **Auto-discovery** of new data sources (30+ RSS feeds, Google News, Reddit)
- **1-second UI refresh** with animated countdown and live indicators
- **Mobile-friendly** responsive layout
- **Zero API keys** required - uses only public RSS feeds

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/referendum-kgraph.git
cd referendum-kgraph
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501 in your browser (works on mobile too).

## Deploy on Streamlit Cloud (Free)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set main file to `app.py`
5. Deploy - you'll get a public URL accessible from any device

## Architecture

| File | Purpose |
|------|---------|
| `app.py` | Streamlit dashboard with live visualization |
| `config.py` | RSS feeds, party positions, polls, sentiment lexicon |
| `data_fetcher.py` | RSS fetching, sentiment analysis, entity extraction |
| `kg_builder.py` | NetworkX knowledge graph construction |
| `predictor.py` | Signal aggregation and prediction engine |
| `source_discovery.py` | Automatic discovery of new data sources |

## Disclaimer

This is an experimental research tool. Predictions are based on public RSS feeds, pre-loaded polls, and simple heuristics. Not a substitute for professional electoral analysis. No quorum is required for this confirmatory constitutional referendum.

## License

MIT
