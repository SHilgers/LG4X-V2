import numpy as np
from lmfit.lineshapes import doniach, gaussian, thermal_distribution
import lmfit
from lmfit import Model
from lmfit.models import guess_from_peak
from scipy.signal import convolve as sc_convolve

# Taken from lmfit/models.py (https://github.com/lmfit/lmfit-py/blob/b930ddef320d93f984181db19fec8e9c9a41be8f/lmfit
# /models.py)
tiny = 1.0e-15


def fwhm_expr(model):
    """Return constraint expression for fwhm."""
    fmt = "{factor:.7f}*{prefix:s}sigma"
    return fmt.format(factor=model.fwhm_factor, prefix=model.prefix)


def dublett(x, amplitude, sigma, gamma, gaussian_sigma, center, soc, height_ratio, fct_coster_kronig):
    """
    Calculates the convolution of a Doniach-Sunjic Dublett with a Gaussian. Thereby, the Gaussian acts as the
    convolution kernel.
    
    Parameters
    ----------
    x: array:
        Array containing the energy of the spectrum to fit
    amplitude: float
        factor used to scale the calculated convolution to the measured spectrum. This factor is used as the amplitude
        of the Doniach profile.
    sigma: float
        Sigma of the Doniach profile
    gamma: float
        asymmetry factor gamma of the Doniach profile
    gaussian_sigma: float
        sigma of the gaussian profile which is used as the convolution kernel
    center: float
        position of the maximum of the measured spectrum
    soc: float
        distance of the second-highest peak (higher-bound-orbital) of the spectrum in relation to the maximum of the
        spectrum (the lower-bound orbital)
    height_ratio: float
        height ratio of the second-highest peak (higher-bound-orbital) of the spectrum in relation to the maximum of
        the spectrum (the lower-bound orbital)
    fct_coster_kronig: float
        ratio of the lorentzian-sigma of the second-highest peak (higher-bound-orbital) of the spectrum in relation to
        the maximum of the spectrum (the lower-bound orbital)
    Returns
    ---------
    array-type
        convolution of a doniach dublett and a gaussian profile
    """
    conv_temp = fft_convolve(
        doniach(x, amplitude=1, center=center, sigma=sigma, gamma=gamma) + doniach(x, height_ratio, center - soc,
                                                                                   fct_coster_kronig * sigma, gamma),
        1 / (np.sqrt(2 * np.pi) * gaussian_sigma) * gaussian(x, amplitude=1, center=np.mean(x), sigma=gaussian_sigma))
    return amplitude * conv_temp / max(conv_temp)


def singlett(x, amplitude, sigma, gamma, gaussian_sigma, center):
    """
    Calculates the convolution of a Doniach-Sunjic with a Gaussian.
    Thereby, the Gaussian acts as the convolution kernel.
    
    Parameters
    ----------
    x: array:
        Array containing the energy of the spectrum to fit
    amplitude: float
        factor used to scale the calculated convolution to the measured spectrum. This factor is used as
        the amplitude of the Doniach profile.
    sigma: float
        Sigma of the Doniach profile
    gamma: float
        asymmetry factor gamma of the Doniach profile
    gaussian_sigma: float
        sigma of the gaussian profile which is used as the convolution kernel
    center: float
        position of the maximum of the measured spectrum
    
    Returns
    ---------
    array-type
        convolution of a doniach profile and a gaussian profile
    """
    conv_temp = fft_convolve(doniach(x, amplitude=1, center=center, sigma=sigma, gamma=gamma),
                             1 / (np.sqrt(2 * np.pi) * gaussian_sigma) * gaussian(x, amplitude=1, center=np.mean(x),
                                                                                  sigma=gaussian_sigma))
    return amplitude * conv_temp / max(conv_temp)


kb = 8.6173e-5  # Boltzmann k in eV/K


def fermi_edge(x, amplitude, center, kt, sigma):
    """
    Calculates the convolution of a Thermal Distribution (Fermi-Dirac Distribution) with a Gaussian.
    Thereby, the Gaussian acts as the convolution kernel.
    
    Parameters
    ----------
    x: array:
        Array containing the energy of the spectrum to fit
    amplitude: float
        factor used to scale the calculated convolution to the measured spectrum. This factor is used
        as the amplitude of the Gaussian Kernel.
    center: float
        position of the step of the fermi edge
    kt: float
        boltzmann constant in eV multiplied with the temperature T in kelvin
        (i.e. for room temperature kt=kb*T=8.6173e-5 eV/K*300K=0.02585 eV)
    sigma: float
        Sigma of the gaussian profile which is used as the convolution kernel
    
    
    
    Returns
    ---------
    array-type
        convolution of a fermi dirac distribution and a gaussian profile
    """
    conv_temp = fft_convolve(thermal_distribution(x, amplitude=1, center=center, kt=kt, form='fermi'),
                             1 / (np.sqrt(2 * np.pi) * sigma) * gaussian(x, amplitude=1, center=np.mean(x),
                                                                         sigma=sigma))
    return amplitude * conv_temp / max(conv_temp)


def convolve(data, kernel):
    """
    Calculates the convolution of a data array with a kernel by using numpy convolve function.
    To suppress edge effects and generate a valid convolution on the full data range, the input dataset is extended
    at the edges.
    
    Parameters
    ----------
    data: array:
        1D-array containing the data to convolve
    kernel: array
        1D-array which defines the kernel used for convolution
    
    Returns
    ---------
    array-type
        convolution of a data array with a kernel array
    
    See Also
    ---------
    numpy.convolve()
    """
    min_num_pts = min(len(data), len(kernel))
    padding = np.ones(min_num_pts)
    padded_data = np.concatenate((padding * data[0], data, padding * data[-1]))
    out = np.convolve(padded_data, kernel, mode='valid')
    n_start_data = int((len(out) - min_num_pts) / 2)
    return (out[n_start_data:])[:min_num_pts]


def fft_convolve(data, kernel):
    """
    Calculates the convolution of a data array with a kernel by using the convolution theorem and thereby
    transforming the time-consuming convolution operation into a multiplication of FFTs.
    For the FFT and inverse FFT, numpy implementation (which is basically the implementation used in scipy)
    of fft and ifft is used.
    To suppress edge effects and generate a valid convolution on the full data range, the input dataset is
    extended at the edges.
    
    Parameters
    ----------
    data: array:
        1D-array containing the data to convolve
    kernel: array
        1D-array which defines the kernel used for convolution
    
    Returns
    ---------
    array-type
        convolution of a data array with a kernel array
    
    See Also
    ---------
    numpy.fft.fft()
    numpy.fft.ifft()
    scipy.fft
    """
    min_num_pts = min(len(data), len(kernel))
    padding = np.ones(min_num_pts)
    padded_data = np.concatenate((padding * data[0], data, padding * data[-1]))
    out = sc_convolve(padded_data, kernel, mode='valid', method="fft")
    n_start_data = int((len(out) - min_num_pts) / 2)
    return (out[n_start_data:])[:min_num_pts]


class ConvGaussianDoniachSinglett(lmfit.model.Model):
    __doc__ = "Model of a Doniach dublett profile convoluted with a gaussian. " \
              "See also lmfit->lineshape.gaussian and lmfit->lineshape.doniach." + lmfit.models.COMMON_INIT_DOC

    def __init__(self, *args, **kwargs):
        super().__init__(singlett, *args, **kwargs)
        self._set_paramhints_prefix()

    def _set_paramhints_prefix(self):
        self.set_param_hint('amplitude', value=100, min=0)
        self.set_param_hint('sigma', value=0.2, min=0)
        self.set_param_hint('gamma', value=0.02, min=0)
        self.set_param_hint('gaussian_sigma', value=0.2, min=0)
        self.set_param_hint('center', value=100, min=0)
        g_fwhm_expr = '2*{pre:s}gaussian_sigma*1.1774'
        self.set_param_hint('gaussian_fwhm', expr=g_fwhm_expr.format(pre=self.prefix))
        l_fwhm_expr = '{pre:s}sigma*(2+{pre:s}gamma*2.5135+({pre:s}gamma*3.6398)**4)'
        self.set_param_hint('lorentzian_fwhm', expr=l_fwhm_expr.format(pre=self.prefix))
        full_fwhm_expr = ("0.5346*{pre:s}lorentzian_fwhm+" +
                          "sqrt(0.2166*{pre:s}lorentzian_fwhm**2+{pre:s}gaussian_fwhm**2)")
        self.set_param_hint('fwhm', expr=full_fwhm_expr.format(pre=self.prefix))
        h_expr = "{pre:s}amplitude"
        self.set_param_hint('height', expr=h_expr.format(pre=self.prefix))
        area_expr = "{pre:s}fwhm*{pre:s}height"
        self.set_param_hint('area', expr=area_expr.format(pre=self.prefix))

    def guess(self, data, x=None, **kwargs):
        if x is None:
            return
        self.set_param_hint('sigma', max=0.3 * (x[-1] - x[0]))
        self.set_param_hint('gaussian_sigma', max=0.3 * (x[-1] - x[0]))
        doniach_pars = guess_from_peak(Model(doniach), data, x, negative=False)
        gaussian_sigma = (doniach_pars["sigma"].value + x[1] - x[
            0]) / 2  # gaussian lies between sigma and the experimental res. why not?
        doniach_ampl = doniach_pars["amplitude"].value * np.sqrt(
            np.sum(gaussian(x=x, amplitude=1, center=np.mean(x), sigma=gaussian_sigma))) / (
                                   2 * np.sqrt(np.sum(x)))  # gives good initial guesses
        params = self.make_params(amplitude=doniach_ampl, sigma=doniach_pars["sigma"].value,
                                  gamma=doniach_pars["gamma"].value, gaussian_sigma=gaussian_sigma,
                                  center=doniach_pars["center"].value)
        return lmfit.models.update_param_vals(params, self.prefix, **kwargs)


class ConvGaussianDoniachDublett(lmfit.model.Model):
    __doc__ = "Model of a Doniach profile convoluted with a gaussian. " \
              "See also lmfit->lineshape.gaussian and lmfit->lineshape.doniach." + lmfit.models.COMMON_INIT_DOC

    def __init__(self, *args, **kwargs):
        super().__init__(dublett, *args, **kwargs)
        self._set_paramhints_prefix()

    def _set_paramhints_prefix(self):
        self.set_param_hint('amplitude', value=100, min=0)
        self.set_param_hint('sigma', value=0.2, min=0)
        self.set_param_hint('gamma', value=0.02, min=0)
        self.set_param_hint('gaussian_sigma', value=0.2, min=0)
        self.set_param_hint('center', value=285)
        self.set_param_hint('soc', value=2.0)
        self.set_param_hint('height_ratio', value=0.75, min=0)
        self.set_param_hint('fct_coster_kronig', value=1, min=0)
        g_fwhm_expr = '2*{pre:s}gaussian_sigma*1.1774'
        self.set_param_hint('gaussian_fwhm', expr=g_fwhm_expr.format(pre=self.prefix))
        l_p1_fwhm_expr = '{pre:s}sigma*(2+{pre:s}gamma*2.5135+({pre:s}gamma*3.6398)**4)'
        l_p2_fwhm_expr = '{pre:s}sigma*(2+{pre:s}gamma*2.5135+({pre:s}gamma*3.6398)**4)*{pre:s}fct_coster_kronig'
        self.set_param_hint('lorentzian_fwhm_p1', expr=l_p1_fwhm_expr.format(pre=self.prefix))
        self.set_param_hint('lorentzian_fwhm_p2', expr=l_p2_fwhm_expr.format(pre=self.prefix))
        fwhm_p1_expr = ("0.5346*{pre:s}lorentzian_fwhm_p1+" +
                        "sqrt(0.2166*{pre:s}lorentzian_fwhm_p1**2+{pre:s}gaussian_fwhm**2)")
        self.set_param_hint('fwhm_p1', expr=fwhm_p1_expr.format(pre=self.prefix))
        fwhm_p2_expr = ("0.5346*{pre:s}lorentzian_fwhm_p2+" +
                        "sqrt(0.2166*{pre:s}lorentzian_fwhm_p2**2+{pre:s}gaussian_fwhm**2)")
        self.set_param_hint('fwhm_p2', expr=fwhm_p2_expr.format(pre=self.prefix))
        h_p1_expr = "{pre:s}amplitude"
        h_p2_expr = "{pre:s}amplitude*{pre:s}height_ratio"
        self.set_param_hint('height_p1', expr=h_p1_expr.format(pre=self.prefix))
        self.set_param_hint('height_p2', expr=h_p2_expr.format(pre=self.prefix))
        area_p1_expr = "{pre:s}fwhm_p1*{pre:s}height_p1"
        self.set_param_hint('area_p1', expr=area_p1_expr.format(pre=self.prefix))
        area_p2_expr = "{pre:s}fwhm_p2*{pre:s}height_p2"
        self.set_param_hint('area_p2', expr=area_p2_expr.format(pre=self.prefix))

    def guess(self, data, x=None, **kwargs):
        if x is None:
            return
        doniach_pars = guess_from_peak(Model(doniach), data, x, negative=False)
        gaussian_sigma = (doniach_pars["sigma"].value + x[1] - x[
            0]) / 2  # gaussian lies between sigma and the experimental res. why not?
        doniach_ampl = doniach_pars["amplitude"].value * np.sqrt(
            np.sum(gaussian(x=x, amplitude=1, center=np.mean(x), sigma=gaussian_sigma))) / (
                                   5 * np.sqrt(np.sum(x)))  # gives good initial guesses
        soc_guess = 0.3 * (
                    x[-1] - x[0])  # assuming a highres spectrum, maybe one could implement a solution with peak-find?
        params = self.make_params(amplitude=doniach_ampl, sigma=doniach_pars["sigma"].value / 5,
                                  gamma=doniach_pars["gamma"].value, gaussian_sigma=gaussian_sigma / 5,
                                  center=doniach_pars["center"].value, soc=soc_guess, height_ratio=1)
        return lmfit.models.update_param_vals(params, self.prefix, **kwargs)


class FermiEdgeModel(lmfit.model.Model):
    __doc__ = "Model of a ThermalDistribution convoluted with a gaussian. " \
              "See also lmfit->lineshape.gaussian and lmfit->lineshape.thermal_distribution." \
              + lmfit.models.COMMON_INIT_DOC

    def __init__(self, *args, **kwargs):
        super().__init__(fermi_edge, *args, **kwargs)
        # limit several input parameters to positive values
        self._set_paramhints_prefix()

    def _set_paramhints_prefix(self):
        self.set_param_hint('kt', value=0.02585, min=0)  # initial value is room temperature
        self.set_param_hint('sigma', value=0.2, min=0)
        self.set_param_hint('center', value=100, min=0)
        self.set_param_hint('amplitude', value=100, min=0)

    def guess(self, data, x=None, **kwargs):
        if x is None:
            return
        self.set_param_hint('center', value=np.mean(x), min=min(x), max=max(x))
        self.set_param_hint('kt', value=kb * 300, min=0, max=kb * 1500)
        self.set_param_hint('amplitude', value=(max(data) - min(data)) / 10, min=0, max=(max(data) - min(data)))
        self.set_param_hint('sigma', value=(max(x) - min(x)) / len(x), min=0, max=2)
        params = self.make_params()
        return lmfit.models.update_param_vals(params, self.prefix, **kwargs)
