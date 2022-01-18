import os
import re

import numpy as np
from numpy.testing import assert_allclose
import pytest
from scipy import stats

from .test_continuous_basic import distcont

# this is not a proper statistical test for convergence, but only
# verifies that the estimate and true values don't differ by too much

fit_sizes = [1000, 5000, 10000]  # sample sizes to try

thresh_percent = 0.25  # percent of true parameters for fail cut-off
thresh_min = 0.75  # minimum difference estimate - true to fail test

mle_failing_fits = [
        'burr',
        'chi2',
        'gausshyper',
        'genexpon',
        'gengamma',
        'kappa4',
        'ksone',
        'kstwo',
        'mielke',
        'ncf',
        'ncx2',
        'pearson3',
        'powerlognorm',
        'truncexpon',
        'tukeylambda',
        'vonmises',
        'levy_stable',
        'trapezoid',
        'studentized_range'
]

mm_failing_fits = ['alpha', 'betaprime', 'burr', 'burr12', 'cauchy', 'chi',
                   'chi2', 'crystalball', 'dgamma', 'dweibull', 'f',
                   'fatiguelife', 'fisk', 'foldcauchy', 'genextreme',
                   'gengamma', 'genhyperbolic', 'gennorm', 'genpareto',
                   'halfcauchy', 'invgamma', 'invweibull', 'johnsonsu',
                   'kappa3', 'ksone', 'kstwo', 'levy', 'levy_l',
                   'levy_stable', 'loglaplace', 'lomax', 'mielke', 'nakagami',
                   'ncf', 'nct', 'ncx2', 'pareto', 'powerlognorm', 'powernorm',
                   'skewcauchy', 't',
                   'trapezoid', 'triang', 'tukeylambda', 'studentized_range']

# not sure if these fail, but they caused my patience to fail
mm_slow_fits = ['argus', 'exponpow', 'exponweib', 'gausshyper', 'genexpon',
                'genhalflogistic', 'halfgennorm', 'gompertz', 'johnsonsb',
                'kappa4', 'kstwobign', 'recipinvgauss', 'skewnorm',
                'truncexpon', 'vonmises', 'vonmises_line']

failing_fits = {"MM": mm_failing_fits + mm_slow_fits, "MLE": mle_failing_fits}

# Don't run the fit test on these:
skip_fit = [
    'erlang',  # Subclass of gamma, generates a warning.
    'genhyperbolic',  # too slow
]


def cases_test_cont_fit():
    # this tests the closeness of the estimated parameters to the true
    # parameters with fit method of continuous distributions
    # Note: is slow, some distributions don't converge with sample
    # size <= 10000
    for distname, arg in distcont:
        if distname not in skip_fit:
            yield distname, arg


@pytest.mark.slow
@pytest.mark.parametrize('distname,arg', cases_test_cont_fit())
@pytest.mark.parametrize('method', ["MLE", 'MM'])
def test_cont_fit(distname, arg, method):
    if distname in failing_fits[method]:
        # Skip failing fits unless overridden
        try:
            xfail = not int(os.environ['SCIPY_XFAIL'])
        except Exception:
            xfail = True
        if xfail:
            msg = "Fitting %s doesn't work reliably yet" % distname
            msg += (" [Set environment variable SCIPY_XFAIL=1 to run this"
                    " test nevertheless.]")
            pytest.xfail(msg)

    distfn = getattr(stats, distname)

    truearg = np.hstack([arg, [0.0, 1.0]])
    diffthreshold = np.max(np.vstack([truearg*thresh_percent,
                                      np.full(distfn.numargs+2, thresh_min)]),
                           0)

    for fit_size in fit_sizes:
        # Note that if a fit succeeds, the other fit_sizes are skipped
        np.random.seed(1234)

        with np.errstate(all='ignore'):
            rvs = distfn.rvs(size=fit_size, *arg)
            est = distfn.fit(rvs, method=method)  # start with default values

        diff = est - truearg

        # threshold for location
        diffthreshold[-2] = np.max([np.abs(rvs.mean())*thresh_percent,
                                    thresh_min])

        if np.any(np.isnan(est)):
            raise AssertionError('nan returned in fit')
        else:
            if np.all(np.abs(diff) <= diffthreshold):
                break
    else:
        txt = 'parameter: %s\n' % str(truearg)
        txt += 'estimated: %s\n' % str(est)
        txt += 'diff     : %s\n' % str(diff)
        raise AssertionError('fit not very good in %s\n' % distfn.name + txt)


def _check_loc_scale_mle_fit(name, data, desired, atol=None):
    d = getattr(stats, name)
    actual = d.fit(data)[-2:]
    assert_allclose(actual, desired, atol=atol,
                    err_msg='poor mle fit of (loc, scale) in %s' % name)


def test_non_default_loc_scale_mle_fit():
    data = np.array([1.01, 1.78, 1.78, 1.78, 1.88, 1.88, 1.88, 2.00])
    _check_loc_scale_mle_fit('uniform', data, [1.01, 0.99], 1e-3)
    _check_loc_scale_mle_fit('expon', data, [1.01, 0.73875], 1e-3)


def test_expon_fit():
    """gh-6167"""
    data = [0, 0, 0, 0, 2, 2, 2, 2]
    phat = stats.expon.fit(data, floc=0)
    assert_allclose(phat, [0, 1.0], atol=1e-3)


class TestFit:
    dist = stats.binom
    rng = np.random.default_rng(49126169847)
    data = stats.binom.rvs(5, 0.5, size=100, random_state=rng)
    shape_bounds_a = [(1, 10), (0, 1)]
    shape_bounds_d = {'n': (1, 10), 'p': (0, 1)}

    def test_dist_iv(self):
        message = "`dist` must be an instance of..."
        with pytest.raises(ValueError, match=message):
            stats.fit(10, self.data, self.shape_bounds_a)

    def test_data_iv(self):
        message = "`data` must be exactly one-dimensional."
        with pytest.raises(ValueError, match=message):
            stats.fit(self.dist, [[1, 2, 3]], self.shape_bounds_a)

        message = "All elements of `data` must be finite numbers."
        with pytest.raises(ValueError, match=message):
            stats.fit(self.dist, [1, 2, 3, np.nan], self.shape_bounds_a)
        with pytest.raises(ValueError, match=message):
            stats.fit(self.dist, [1, 2, 3, np.inf], self.shape_bounds_a)
        with pytest.raises(ValueError, match=message):
            stats.fit(self.dist, ['1', '2', '3'], self.shape_bounds_a)

    def test_shape_bounds_iv(self):
        message = "Bounds provided for the following unrecognized shapes..."
        shape_bounds = {'n': (1, 10), 'p': (0, 1), '1': (0, 10)}
        with pytest.warns(RuntimeWarning, match=message):
            stats.fit(self.dist, self.data, shape_bounds)

        message = "`shape_bounds` must have 2 elements..."
        shape_bounds = [(1, 10)]
        with pytest.raises(ValueError, match=message):
            stats.fit(self.dist, self.data, self.shape_bounds_a[:1])
        shape_bounds = [(1, 10, 3), (0, 1, 0.5)]
        with pytest.raises(ValueError, match=message):
            stats.fit(self.dist, self.data, shape_bounds)
        shape_bounds = [(1), (0)]
        with pytest.raises(ValueError, match=message):
            stats.fit(self.dist, self.data, shape_bounds)

        message = "There are no values for `p` on the interval..."
        shape_bounds = {'n': (1, 10), 'p': (1, 0)}
        with pytest.raises(ValueError, match=message):
            stats.fit(self.dist, self.data, shape_bounds)

        message = "There are no values for `n` on the interval..."
        shape_bounds = [(10, 1), (0, 1)]
        with pytest.raises(ValueError, match=message):
            stats.fit(self.dist, self.data, shape_bounds)

        message = "There are no integer values for `n` on the interval..."
        shape_bounds = [(1.4, 1.6), (0, 1)]
        with pytest.raises(ValueError, match=message):
            stats.fit(self.dist, self.data, shape_bounds)

        message = "The intersection of user-provided bounds for `n`"
        shape_bounds = [(-np.inf, np.inf), (0, 1)]
        with pytest.raises(ValueError, match=message):
            stats.fit(self.dist, self.data, shape_bounds)

    def test_loc_bounds_iv(self):
        message = "`loc_bounds` must be a tuple containing exactly two..."
        loc_bounds = (0, 1, 2)
        with pytest.raises(ValueError, match=message):
            stats.fit(self.dist, self.data, self.shape_bounds_a,
                      loc_bounds=loc_bounds)

        message = "There are no values for `loc` on the interval..."
        loc_bounds = (10, 0)
        with pytest.raises(ValueError, match=message):
            stats.fit(self.dist, self.data, self.shape_bounds_a,
                      loc_bounds=loc_bounds)

        message = "There are no integer values for `loc` on the interval..."
        loc_bounds = (0.4, 0.6)
        with pytest.raises(ValueError, match=message):
            stats.fit(self.dist, self.data, self.shape_bounds_a,
                      loc_bounds=loc_bounds)

        message = "The intersection of user-provided bounds for `loc`"
        loc_bounds = (-np.inf, np.inf)
        with pytest.raises(ValueError, match=message):
            stats.fit(self.dist, self.data, self.shape_bounds_a,
                      loc_bounds=loc_bounds)

    def test_scale_bounds_iv(self):

        message = "`binom` is an instance of `rv_discrete`..."
        scale_bounds = (1, 10)
        with pytest.warns(RuntimeWarning, match=message):
            stats.fit(self.dist, self.data, self.shape_bounds_a,
                      scale_bounds=scale_bounds)

        message = "`scale_bounds` must be a tuple containing exactly two..."
        scale_bounds = (0, 1, 2)
        with pytest.raises(ValueError, match=message):
            stats.fit(stats.norm, self.data, scale_bounds=scale_bounds)
        with pytest.raises(ValueError, match=message):
            stats.fit(stats.norm, self.data, [], scale_bounds=scale_bounds)

        message = "There are no values for `scale` on the interval..."
        scale_bounds = (10, 0)
        with pytest.raises(ValueError, match=message):
            stats.fit(stats.norm, self.data, scale_bounds=scale_bounds)

        message = "The intersection of user-provided bounds for `scale`"
        scale_bounds = (1, np.inf)
        with pytest.raises(ValueError, match=message):
            stats.fit(stats.norm, self.data, scale_bounds=scale_bounds)
