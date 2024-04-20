import anacal
import fpfs
import galsim
import numpy as np


def test_noise_covariance():
    variance = 0.22**2.0
    sigma_as = 0.55
    nord = 4
    det_nrot = 4
    pixel_scale = 0.2
    ngrid = 64
    psf_obj = galsim.Moffat(beta=3.5, fwhm=0.6, trunc=0.6 * 4.0)
    psf_obj = psf_obj.shear(e1=0.02, e2=-0.02)
    psf_array = (
        psf_obj.shift(0.5 * pixel_scale, 0.5 * pixel_scale)
        .drawImage(nx=ngrid, ny=ngrid, scale=pixel_scale)
        .array
    )

    noise_task = fpfs.image.measure_noise_cov(
        psf_array,
        sigma_arcsec=sigma_as,
        nord=nord,
        pixel_scale=pixel_scale,
        det_nrot=det_nrot,
    )
    # NOTE: this is the power function of noise not the noise power spectrum!!
    # Namely, it is the expectation of the power of the Fourier transform of
    # noise images
    noise_pow = np.ones((ngrid, ngrid)) * variance * ngrid**2.0
    cov_elem = noise_task.measure(noise_pow)
    noise_task2 = anacal.fpfs.FpfsNoiseCov(
        psf_array,
        pixel_scale,
        sigma_as,
        nord,
        det_nrot,
        klim_thres=1e-20,
    )
    cov_elem2 = noise_task2.measure(variance=variance)
    np.testing.assert_allclose(cov_elem, cov_elem2, atol=1e-6, rtol=0)
    return
