import gc
import time

import anacal
import fpfs
import galsim
import numpy as np

from . import mem_used, print_mem


def test_memory():
    pthres = 0.2
    pratio = 0.05
    std = 0.4

    ny = 5010
    nx = 5010
    scale = 0.2
    sigma_as = 0.55
    det_task = anacal.fpfs.FpfsDetect(
        scale=scale,
        sigma_arcsec=sigma_as,
        det_nrot=4,
        klim=10.0,
    )
    psf_obj = galsim.Moffat(beta=3.5, fwhm=0.6, trunc=0.6 * 4.0).shear(
        e1=0.02, e2=-0.02
    )
    psf_data = (
        psf_obj.shift(0.5 * scale, 0.5 * scale)
        .drawImage(nx=64, ny=64, scale=scale)
        .array
    )
    gal_obj = (
        psf_obj.shift(-3.5, 2) * 2
        + psf_obj.shift(2, -1) * 4
        + psf_obj.shift(-2, -0.5) * 4
        + psf_obj.shift(-3.2, 0.5) * 6
    )
    gal_data = gal_obj.drawImage(nx=nx, ny=ny, scale=scale).array

    initial_memory_usage = mem_used()
    print_mem(initial_memory_usage)
    t0 = time.time()
    for _ in range(3):
        noise_data = np.random.randn(ny, nx)
        smooth_data = det_task.smooth_image(
            gal_array=gal_data, psf_array=psf_data, noise_array=noise_data
        )
        out1 = det_task.detect_peaks(
            smooth_data,
            fthres=1.0,
            pthres=pthres,
            pratio=pratio,
            bound=2,
            std_m00=std * scale**2.0,
            std_v=std * scale**2.0,
        )
        print_mem(mem_used() - initial_memory_usage)
        del noise_data, out1, smooth_data
    t1 = time.time()
    print("Time: ", t1 - t0)
    gc.collect()
    final_memory_usage = mem_used()
    print_mem(final_memory_usage - initial_memory_usage)
    return


if __name__ == "__main__":
    test_memory()
