![deploy MCASS dashboard](https://github.com/hydrosolutions/MCASS/actions/workflows/docker.yml/badge.svg)

# MCASS

Interactive dashboard for visualizing snow water storage in mountainous Central Asia.

**Live app:** [https://snowmapper.ch](https://snowmapper.ch)

## About

This dashboard visualizes snow water storage data from the [snowmapperForecast](https://github.com/joelfiddes/snowmapperForecast) model, an operational version of [TopoPyScale](https://github.com/ArcticSnow/TopoPyScale) running the [Factorial Snow Model (FSM)](https://github.com/RichardEssery/FSM). The model is deployed by [@joelfiddes](https://github.com/joelfiddes/) at the Swiss Federal Institute for Snow and Avalanche Research (SLF).

## Data Format

The dashboard expects two CSV files per basin in the data directory:
- `<basin_code>_current.txt` - Current year data
- `<basin_code>_climate.txt` - Long-term average data

Required columns:
| Column | Description |
|--------|-------------|
| `date` | Date (current year) |
| `Q5_SWE` | 5th percentile snow water equivalent |
| `Q50_SWE` | Median snow water equivalent |
| `Q95_SWE` | 95th percentile snow water equivalent |
| `Q5_HS` | 5th percentile snow depth |
| `Q50_HS` | Median snow depth |
| `Q95_HS` | 95th percentile snow depth |

## Local Development

1. Clone the repository and create a conda environment:
   ```bash
   conda create --name mcass
   conda activate mcass
   pip install -r requirements.txt
   ```

2. Configure the data path in `.env`:
   ```
   MCASS_DATA_PATH=<path-to-data>
   ```

3. Generate dummy data if needed (from the `tools/` directory):
   ```bash
   jupyter nbconvert --execute --clear-output generate_dummy_data.ipynb
   ```

4. Run the dashboard:
   ```bash
   panel serve mcass-dashboard.py --show --autoreload --port 5010
   ```

## Docker Deployment

Pull and run the container:
```bash
docker pull mabesa/mcass-dashboard:latest
docker run -d -v /path/to/data:/app/data -p 5006:5006 --name mcass-dashboard mabesa/mcass-dashboard
```

Commits to `main` trigger automated deployment via GitHub Actions and Watchtower.

## License

MIT
