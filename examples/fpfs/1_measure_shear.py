import fitsio
import anacal
import numpy as np


pixel_scale = 0.2
noise_variance = 0.23
seed = 1


fpfs_config = anacal.fpfs.FpfsConfig()

gal_array = fitsio.read("image-00000_g1-0_rot0_i.fits")
psf_array = fitsio.read("PSF_Fixed.fits")

# Preparing
if noise_variance <= 0:
    raise ValueError(
        "Noise variance should be positive, even though",
        "image is noiseless.",
    )
ngrid = fpfs_config.rcut * 2
if not psf_array.shape == (ngrid, ngrid):
    raise ValueError("psf arry has a wrong shape")
ny, nx = gal_array.shape
if fpfs_config.noise_rev:
    noise_array = np.random.RandomState(seed).normal(
        scale=np.sqrt(noise_variance),
        size=(ny, nx),
    )
else:
    noise_array = None

# Shapelet Covariance matrix
noise_task = anacal.fpfs.FpfsNoiseCov(
    psf_array=psf_array,
    pixel_scale=pixel_scale,
    sigma_arcsec=fpfs_config.sigma_arcsec,
    nord=fpfs_config.nord,
    det_nrot=fpfs_config.det_nrot,
    klim_thres=fpfs_config.klim_thres,
)
cov_matrix = noise_task.measure(variance=noise_variance)
print(np.diag(cov_matrix))
del noise_task

# Detection
dtask = anacal.fpfs.FpfsDetect(
    nx=ny,
    ny=nx,
    psf_array=psf_array,
    pixel_scale=pixel_scale,
    sigma_arcsec=fpfs_config.sigma_arcsec,
    cov_matrix=cov_matrix,
    det_nrot=fpfs_config.det_nrot,
    klim_thres=fpfs_config.klim_thres,
)
coords = dtask.run(
    gal_array=gal_array,
    fthres=8.5,
    pthres=fpfs_config.pthres,
    pratio=fpfs_config.pratio,
    pthres2=fpfs_config.pthres2,
    bound=fpfs_config.bound,
    noise_array=noise_array,
)
del dtask

mtask = anacal.fpfs.FpfsMeasure(
    psf_array=psf_array,
    pixel_scale=pixel_scale,
    sigma_arcsec=fpfs_config.sigma_arcsec,
    det_nrot=fpfs_config.det_nrot,
    klim_thres=fpfs_config.klim_thres,
)
src = mtask.run(gal_array=gal_array, det=coords)
if noise_array is not None:
    noise_src = mtask.run(noise_array, det=coords, do_rotate=True)
    src = src + noise_src
else:
    noise_src = None
sel = (src[:, mtask.di["m00"]] + src[:, mtask.di["m20"]]) > 1e-5
coords = np.array(coords)[sel]
print(len(coords))
src = src[sel]
if noise_src is not None:
    noise_src = noise_src[sel]
del mtask, sel

# Catalog
ctask = anacal.fpfs.FpfsCatalog(
    cov_mat=cov_matrix,
    snr_min=fpfs_config.snr_min,
    r2_min=fpfs_config.r2_min,
    c0=fpfs_config.c0,
    c2=fpfs_config.c2,
    alpha=fpfs_config.alpha,
    beta=fpfs_config.beta,
    pthres=fpfs_config.pthres,
    pratio=fpfs_config.pratio,
    pthres2=fpfs_config.pthres2,
    det_nrot=fpfs_config.det_nrot,
)
out = ctask.measure_g1_renoise(src, noise_src)
print(np.sum(out[:, 0]) / np.sum(out[:, 1]))
del ctask
