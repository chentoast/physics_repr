# Just-in-Time World Modeling

This repository contains code and data for the paper **"Just-in-Time World Modeling Supports Human Planning and Reasoning."**

---

## Directory Structure

```
plinko-repro/
├── data/              # Experimental data (CSV, JSON) and analysis notebooks
├── models/            # Model fitting code and cached predictions
├── experiments/       # Web experiment platform (JavaScript + HTML)
├── stimuli/           # Scripts to generate experiment stimuli
├── pyGameWorld/       # Physics simulation engine
├── navigation/        # Planning and GridWorld results
├── figures/           # Publication figures (PDFs)
└── figures.ipynb      # Notebook for the model diagram figure
```

### Key entry points

| What you want to do | Where to look |
|---|---|
| Reproduce experimental figures | Notebooks inside `data/` |
| Reproduce navigation figures | `navigation/{viz,simulation_analysis}.ipynb` |
| Run the web experiment locally | `experiments/app.js` |
| Refit computational models | `models/fit_models.py` |
| Regenerate stimuli | `stimuli/prepare_*.py` scripts |

---

## Installation & Setup

### Python environment

The analysis code requires **Python 3.9+**. We recommend using a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> **Note:** `rpy2` requires a working R installation on your system. It is only needed for specific analyses; most figures can be reproduced without it.

### Jupyter notebooks

After installing dependencies, run `jupyter lab` from the repo root and open the relevant notebook from there.

### Web experiment (JavaScript)

To run the experiment locally, you'll need [Node.js](https://nodejs.org) (v16+):

```bash
cd experiments
npm install
node app.js
```

The experiment will be served at `http://localhost:3000` (or whichever port is configured in `app.js`).

### Navigation submodule

The `navigation/` directory includes a Git submodule (`value-guided-construal`). After cloning the repo, initialize it with:

```bash
git submodule update --init --recursive
```

---

## Data

Raw experimental data lives in `data/` and `navigation/data/`. The directory names differ from the paper's labels:

| Directory | Paper name |
|---|---|
| `exp1/` | Exp 2A |
| `exp_vgc2/` | Exp 2B |
| `exp_background/` | Exp S1 |
| `exp_teleporter/` | Exp S2 |
| `exp_likelihood/` | Exp S3 |

Cached model predictions are stored in `models/output/` and `navigation/output/`, so you can reproduce figures without re-running the (potentially slow) model fitting step.
