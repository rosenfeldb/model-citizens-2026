"""Pick strategies, a simulated field of rival entrants, and a P(win) optimizer.

A pick vector x has x_i = 1 for the left-side candidate, 0 for the right.
Score in one simulated election = sum_i L_i(pick) * [pick won], with
L = -log2(max(Kalshi price, 1%)).
"""
import numpy as np
import pandas as pd
from scipy.special import ndtr
from scipy.stats import norm

FLOOR = 0.01


def points(races):
    Ll = -np.log2(np.maximum(races.price_left.values, FLOOR))
    Lr = -np.log2(np.maximum(races.price_right.values, FLOOR))
    fixed = races.fixed.values.astype(bool)
    Ll[fixed] = 0.0
    Lr[fixed] = 0.0
    return Ll.astype(np.float32), Lr.astype(np.float32)


def scores(W, X, Ll, Lr):
    """W: n x R outcomes (left won). X: R or R x M picks. Returns n or n x M."""
    Wf = W.astype(np.float32)
    X = X.astype(np.float32)
    if X.ndim == 1:
        return Wf @ (X * Ll) + (1 - Wf) @ ((1 - X) * Lr)
    return Wf @ (X * Ll[:, None]) + (1 - Wf) @ ((1 - X) * Lr[:, None])


# ---------------------------------------------------------------- strategies
def chalk(q, Ll, Lr):
    return (q > 0.5).astype(int)


def ev_max(q, Ll, Lr):
    return (q * Ll > (1 - q) * Lr).astype(int)


def all_underdogs(q, Ll, Lr):
    return (q < 0.5).astype(int)


def upset_threshold(tau):
    """Favorite, except take the underdog when its probability is at least tau."""
    def f(q, Ll, Lr):
        x = (q > 0.5).astype(int)
        und = np.minimum(q, 1 - q)
        flip = und >= tau
        x[flip] = 1 - x[flip]
        return x
    f.__name__ = f"upsets>={tau:.0%}"
    return f


def lean_left(tau):
    """Wave bet: the left/Democratic side wherever its chance is >= tau."""
    def f(q, Ll, Lr):
        return (q >= tau).astype(int)
    f.__name__ = f"D-wave(q>={tau:.0%})"
    return f


def lean_right(tau):
    """Polling-miss bet: the right/Republican side wherever its chance is >= tau."""
    def f(q, Ll, Lr):
        return ((1 - q) < tau).astype(int)
    f.__name__ = f"R-rebound(q_R>={tau:.0%})"
    return f


def baseline_strategies():
    return [chalk, ev_max, all_underdogs, upset_threshold(0.10), upset_threshold(0.20),
            upset_threshold(0.30), lean_left(0.05), lean_left(0.15), lean_right(0.05), lean_right(0.15)]


# ---------------------------------------------------------------- the field
FIELDS = {
    # share of entrants by type: chalk, upset-hunter, EV-maximizer, all-underdog
    "naive": {"chalk": 0.70, "upset": 0.20, "ev": 0.08, "under": 0.02},
    "mixed": {"chalk": 0.50, "upset": 0.25, "ev": 0.20, "under": 0.05},
    "savvy": {"chalk": 0.30, "upset": 0.25, "ev": 0.35, "under": 0.10},
}


def make_pool(races, Ll, Lr, mix, m=800, seed=1):
    """m rival pick vectors. Rivals build their own noisy beliefs around the market."""
    rng = np.random.default_rng(seed)
    z = norm.ppf(np.clip(races.p_mkt.values, 1e-4, 1 - 1e-4))
    fixed = races.fixed.values.astype(bool)
    types = rng.choice(list(mix), size=m, p=list(mix.values()))
    X = np.zeros((len(races), m), dtype=np.int8)
    for j, t in enumerate(types):
        lam = rng.uniform(0.9, 1.4)
        bias = rng.normal(0, 0.15)             # some models lean one party
        noise = rng.uniform(0.1, 0.6)          # how far their model strays from the market
        qj = norm.cdf(lam * z + bias + rng.normal(0, noise, len(z)))
        if t == "chalk":
            x = qj > 0.5
        elif t == "ev":
            x = qj * Ll > (1 - qj) * Lr
        elif t == "upset":
            x = qj > 0.5
            flip = np.minimum(qj, 1 - qj) >= rng.uniform(0.08, 0.35)
            x = np.where(flip, ~x, x)
        else:
            x = qj < 0.5
        x = x.astype(np.int8)
        x[fixed] = (races.q.values[fixed] > 0.5)
        X[:, j] = x
    return X, types


def field_max(pool_scores, n_rivals, seed=2):
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, pool_scores.shape[1], (pool_scores.shape[0], n_rivals))
    return np.take_along_axis(pool_scores, idx, axis=1).max(axis=1)


def p_win(s, fmax):
    return float(np.mean(s > fmax) + 0.5 * np.mean(s == fmax))


# ---------------------------------------------------------------- optimizer
def optimize(x0, W, Ll, Lr, fmax, temp=0.5, max_iter=600, locked=None):
    """Greedy coordinate ascent on a smoothed P(win) = mean Phi((score - field max)/temp)."""
    x = x0.astype(np.int8).copy()
    Wf = W.astype(np.float32)
    A = Wf * Ll - (1 - Wf) * Lr                     # left-minus-right contribution, n x R
    s = scores(W, x, Ll, Lr)
    gap = (s - fmax).astype(np.float32)
    cur = ndtr(gap / temp).mean()
    for _ in range(max_iter):
        delta = A * (1 - 2 * x).astype(np.float32)  # change in score if race i flips
        val = ndtr((gap[:, None] + delta) / temp).mean(axis=0)
        if locked is not None:
            val[locked] = -1
        i = int(np.argmax(val))
        if val[i] <= cur + 1e-6:
            break
        x[i] = 1 - x[i]
        gap = gap + delta[:, i]
        cur = val[i]
    return x
