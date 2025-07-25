# Heat Insights Notebooks

GEE-based data analysis environment for heat studies with interactive visualizations.

## Setup

1. Create Python environment:
```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up GEE authentication (follow prompts)

4. Start Jupyter:
```bash
jupyter lab
```

## Project Structure

- `notebooks/` - Analysis notebooks
- `src/` - Reusable Python modules  
- `data/` - Input datasets
- `outputs/` - Generated maps and charts
- `config/` - Configuration files