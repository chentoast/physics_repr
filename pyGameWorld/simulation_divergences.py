import numpy as np
import scipy.stats as sps
from scipy.special import logsumexp
from sklearn.neighbors import KernelDensity


def ks(sim_endpos1, sim_endpos2):
    ks = sps.ks_2samp(sim_endpos1, sim_endpos2).statistic
    return ks


def kl_kde(sim_endpos1, sim_endpos2):
    kde1 = KernelDensity().fit(sim_endpos1[:, None])
    kde2 = KernelDensity().fit(sim_endpos2[:, None])

    # calculate kl divergence between the two histograms
    grid = np.linspace(0, 600, 1000)
    # breakpoint()
    ll1 = kde1.score_samples(grid[:, None])
    ll2 = kde2.score_samples(grid[:, None])
    ll1 -= logsumexp(ll1)
    ll2 -= logsumexp(ll2)

    kl = np.sum(np.exp(ll1) * (ll1 - ll2))
    return kl


def js_kde(sim_endpos1, sim_endpos2):
    kde1 = KernelDensity().fit(sim_endpos1[:, None])
    kde2 = KernelDensity().fit(sim_endpos2[:, None])

    # calculate kl divergence between the two histograms
    grid = np.linspace(0, 600, 1000)
    # print(np.logaddexp(
    #             kde1.score_samples(grid[:, None]), kde2.score_samples(grid[:, None])
    #         ).shape)
    ll1 = kde1.score_samples(grid[:, None])
    ll2 = kde2.score_samples(grid[:, None])
    ll1 -= logsumexp(ll1)
    ll2 -= logsumexp(ll2)

    # breakpoint()
    kl1 = np.sum(np.exp(ll1) * (ll1 - np.logaddexp(ll1, ll2) + np.log(2)))
    kl2 = np.sum(np.exp(ll2) * (ll2 - np.logaddexp(ll1, ll2) + np.log(2)))
    return 0.5 * (kl1 + kl2)


def kl(sim_endpos1, sim_endpos2):
    n_bins = 15
    hist, _ = np.histogram(sim_endpos1, bins=n_bins, density=True)
    hist_modified, _ = np.histogram(sim_endpos2, bins=n_bins, density=True)

    overlap = [i for i in range(n_bins) if hist[i] > 0 and hist_modified[i] > 0]
    hist = hist[overlap]
    hist_modified = hist_modified[overlap]

    # calculate kl divergence between the two histograms
    kl = np.sum(hist * (np.log(hist) - np.log(hist_modified)))
    return kl


def js(sim_endpos1, sim_endpos2):
    n_bins = 30
    hist, _ = np.histogram(sim_endpos1, bins=n_bins, density=True)
    hist_modified, _ = np.histogram(sim_endpos2, bins=n_bins, density=True)
    # calculate kl divergence between the two histograms
    joint = (hist + hist_modified) / 2

    overlap = [i for i in range(n_bins) if hist[i] > 0 and hist_modified[i] > 0]
    hist = hist[overlap]
    hist_modified = hist_modified[overlap]
    joint = joint[overlap]

    kl1 = np.sum(hist * (np.log(hist) - np.log(joint)))
    kl2 = np.sum(hist_modified * (np.log(hist_modified) - np.log(joint)))
    return kl1 + kl2

# wasserstein distance with p=1
def mae(sim_endpos1, sim_endpos2):
    sim_endpos1 = np.array(sorted(sim_endpos1))
    sim_endpos2 = np.array(sorted(sim_endpos2))

    mae = np.abs(sim_endpos1 - sim_endpos2)

    return mae.mean()
