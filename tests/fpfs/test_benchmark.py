import gc
import time

import anacal
import galsim
import numpy as np
from memory_profiler import memory_usage

from .. import mem_used, print_mem

ny = 5000
nx = 5000

std = 0.4
nord = 4
det_nrot = 4
bound = 40
mag_zero = 30.0
pixel_scale = 0.2

sigma_arcsec = 0.55
psf_obj = galsim.Moffat(beta=3.5, fwhm=0.6, trunc=0.6 * 4.0).shear(
    e1=0.02, e2=-0.02
)
psf_data = (
    psf_obj.shift(0.5 * pixel_scale, 0.5 * pixel_scale)
    .drawImage(nx=64, ny=64, scale=pixel_scale)
    .array
).astype(np.float64)
gal_obj = (
    psf_obj.shift(-3.5, 2) * 2
    + psf_obj.shift(2, -1) * 4
    + psf_obj.shift(-2, -0.5) * 4
    + psf_obj.shift(-3.2, 0.5) * 6
)
gal_data = gal_obj.drawImage(
    nx=nx,
    ny=ny,
    scale=pixel_scale,
).array.astype(np.float32)


def test_benchmark():
    print("")
    initial_memory_usage = mem_used()

    def func():
        noise_data = np.random.randn(ny, nx)
        t0 = time.time()

        cov_matrix = np.ones((21, 21)) * (std * pixel_scale) ** 2.0
        cov_matrix = anacal.fpfs.table.Covariance(
            array=cov_matrix,
            nord=nord,
            det_nrot=det_nrot,
            pixel_scale=pixel_scale,
            mag_zero=mag_zero,
            sigma_arcsec=sigma_arcsec,
        )
        dtask = anacal.fpfs.FpfsDetect(
            mag_zero=mag_zero,
            psf_array=psf_data,
            pixel_scale=pixel_scale,
            cov_matrix=cov_matrix,
            sigma_arcsec=sigma_arcsec,
            det_nrot=det_nrot,
            bound=bound,
        )
        t1 = time.time()
        print("Detection Time: ", t1 - t0)
        det = dtask.run(
            gal_array=gal_data,
            fthres=1.0,
            pthres=anacal.fpfs.fpfs_det_sigma2 + 0.02,
            noise_array=noise_data,
        )[0:30000]
        mtask = anacal.fpfs.FpfsMeasure(
            mag_zero=mag_zero,
            psf_array=psf_data,
            pixel_scale=pixel_scale,
            sigma_arcsec=sigma_arcsec,
            nord=nord,
            det_nrot=det_nrot,
        )
        src = mtask.run(
            gal_array=gal_data,
            det=det,
        )
        t2 = time.time()
        print("Final Time: ", t2 - t0)
        del noise_data, det, src, dtask, mtask
        return

    print("Initial Mem:")
    print_mem(initial_memory_usage)
    func()

    peak_memory_usage = max(memory_usage(proc=(func,)))
    print("Peak Mem:", peak_memory_usage, "M")
    gc.collect()
    final_memory_usage = mem_used()
    print("Additional Mem:")
    print_mem(final_memory_usage - initial_memory_usage)
    return


if __name__ == "__main__":
    test_benchmark()
