"""Correlated election simulator (Gaussian factor copula).

Left-side margin in race i:
    m_i = mu_i + N + REGION[r(i)] + STATE[s(i)] + h_i * HISP + e_i
    N     national swing          sd SIGMA["national"]
    REGION census division        sd SIGMA["region"]
    STATE  shared by every race in a state (Senate + House)
    HISP   extra swing shared by heavily Hispanic districts
    e_i    race-specific noise    sd SIGMA["house"] or SIGMA["senate"]
mu_i is set so that P(m_i > 0) = q_i exactly, so the simulator never changes a
race's own probability; it only adds realistic co-movement between races.
"""
import numpy as np
import pandas as pd

SIGMA = {"national": 3.0, "region": 1.5, "state": 2.0, "hisp": 3.0, "house": 5.0, "senate": 4.0}

DIVISION = {
    "CT": 1, "ME": 1, "MA": 1, "NH": 1, "RI": 1, "VT": 1,
    "NJ": 2, "NY": 2, "PA": 2,
    "IL": 3, "IN": 3, "MI": 3, "OH": 3, "WI": 3,
    "IA": 4, "KS": 4, "MN": 4, "MO": 4, "NE": 4, "ND": 4, "SD": 4,
    "DE": 5, "FL": 5, "GA": 5, "MD": 5, "NC": 5, "SC": 5, "VA": 5, "WV": 5, "DC": 5,
    "AL": 6, "KY": 6, "MS": 6, "TN": 6,
    "AR": 7, "LA": 7, "OK": 7, "TX": 7,
    "AZ": 8, "CO": 8, "ID": 8, "MT": 8, "NV": 8, "NM": 8, "UT": 8, "WY": 8,
    "AK": 9, "CA": 9, "HI": 9, "OR": 9, "WA": 9,
}
HISPANIC = {"TX-09", "TX-15", "TX-23", "TX-28", "TX-34", "TX-35", "FL-25", "FL-26", "FL-27", "FL-28",
            "CA-13", "CA-21", "CA-22", "NM-02", "NV-01", "NV-03", "NV-04", "AZ-07", "CO-08", "NM-SEN"}


def factor_structure(races, sigma=SIGMA):
    """Return per-race total sd and index arrays for each shared factor."""
    st = races.race_id.str[:2].values
    states = sorted(set(st))
    st_idx = np.array([states.index(s) for s in st])
    div_idx = np.array([DIVISION[s] - 1 for s in st])
    hisp = races.race_id.isin(HISPANIC).values.astype(float)
    idio = np.where(races.chamber.values == "Senate", sigma["senate"], sigma["house"])
    total = np.sqrt(sigma["national"] ** 2 + sigma["region"] ** 2 + sigma["state"] ** 2
                    + (hisp * sigma["hisp"]) ** 2 + idio ** 2)
    return total, st_idx, div_idx, hisp, idio, len(states)


def simulate(races, n, seed=0, sigma=SIGMA, national_shift=0.0):
    """Boolean matrix (n x races): True where the left-side candidate wins.

    national_shift moves every race's expected margin (in points) toward the
    left; it is used for stress tests, not for the main forecast.
    """
    from scipy.stats import norm
    rng = np.random.default_rng(seed)
    q = races.q.values
    total, st_idx, div_idx, hisp, idio, n_states = factor_structure(races, sigma)
    mu = total * norm.ppf(np.clip(q, 1e-6, 1 - 1e-6)) + national_shift
    N = rng.normal(0, sigma["national"], (n, 1))
    REG = rng.normal(0, sigma["region"], (n, 9))[:, div_idx]
    STA = rng.normal(0, sigma["state"], (n, n_states))[:, st_idx]
    HIS = rng.normal(0, sigma["hisp"], (n, 1)) * hisp
    E = rng.normal(0, 1, (n, len(races))) * idio
    margin = mu + N + REG + STA + HIS + E
    W = margin > 0
    fixed = races.fixed.values.astype(bool)
    W[:, fixed] = (q[fixed] > 0.5)
    return W, N.ravel()
