from numpy.typing import NDArray
from pydantic import BaseModel, Field

from .._anacal.fpfs import (
    FpfsImage,
    fpfs_cut_sigma_ratio,
    fpfs_det_sigma2,
    fpfs_pnr,
)
from .._anacal.image import Image
from .._anacal.mask import mask_galaxy_image
from .._anacal.psf import BasePsf
from . import base, table
from .ctask import CatalogTask, CatTaskD, CatTaskM
from .itask import FpfsDetect, FpfsMeasure, FpfsNoiseCov

__all__ = [
    "base",
    "table",
    "FpfsImage",
    "FpfsNoiseCov",
    "FpfsDetect",
    "FpfsMeasure",
    "FpfsConfig",
    "CatTaskD",
    "CatTaskM",
    "CatalogTask",
]


class FpfsConfig(BaseModel):
    rcut: int = Field(
        default=32,
        description="""Galaxies are put into stamp before measurement, rcut
            is the radius of the cut
        """,
    )
    nord: int = Field(
        default=4,
        description="""Maximum radial number `n` to use for the shapelet basis
        """,
    )
    det_nrot: int = Field(
        default=4,
        description="""Number of directions to calculate when detecting the
            peaks.
        """,
    )
    klim_thres: float = Field(
        default=1e-12,
        description="""The threshold used to define the upper limit of k we use
        in Fourier space.
        """,
    )
    bound: int = Field(
        default=35,
        description="""Boundary buffer length, the sources in the buffer reion
        are not counted.
        """,
    )
    sigma_arcsec: float = Field(
        default=0.52,
        description="""Smoothing scale of the shapelet and detection kernel.
        """,
    )
    pthres: float = Field(
        default=0.12,
        description="""Detection threshold (peak identification) for the
        pooling.
        """,
    )
    fthres: float = Field(
        default=8.5,
        description="""Detection threshold (minimum signal-to-noise ratio) for
        the first pooling.
        """,
    )
    snr_min: float = Field(
        default=12,
        description="""Minimum Signal-to-Noise Ratio.
        """,
    )
    r2_min: float = Field(
        default=0.1,
        description="""Minimum resolution.
        """,
    )
    c0: float = Field(
        default=5.0,
        description="""Weighting parameter for m00 for ellipticity definition.
        """,
    )


def process_image(
    fpfs_config: FpfsConfig,
    gal_array: NDArray,
    psf_array: NDArray,
    pixel_scale: float,
    noise_variance: float,
    noise_array: NDArray,
    coords: NDArray,
    mag_zero: float = 30.0,
):
    # Preparing
    ngrid = fpfs_config.rcut * 2
    if not psf_array.shape == (ngrid, ngrid):
        raise ValueError("psf arry has a wrong shape")
    ny, nx = gal_array.shape

    # Shapelet Covariance matrix
    if noise_variance <= 0:
        raise ValueError(
            "To enable detection, noise variance should be positive, ",
            "even though image is noiseless.",
        )
    noise_task = FpfsNoiseCov(
        mag_zero=mag_zero,
        psf_array=psf_array,
        pixel_scale=pixel_scale,
        sigma_arcsec=fpfs_config.sigma_arcsec,
        nord=fpfs_config.nord,
        det_nrot=fpfs_config.det_nrot,
        klim_thres=fpfs_config.klim_thres,
    )
    cov_matrix = noise_task.measure(variance=noise_variance)
    del noise_task

    # Detection
    if coords is None:
        dtask = FpfsDetect(
            nx=ny,
            ny=nx,
            mag_zero=mag_zero,
            psf_array=psf_array,
            pixel_scale=pixel_scale,
            sigma_arcsec=fpfs_config.sigma_arcsec,
            cov_matrix=cov_matrix,
            det_nrot=fpfs_config.det_nrot,
            klim_thres=fpfs_config.klim_thres,
        )
        coords = dtask.run(
            gal_array=gal_array,
            fthres=fpfs_config.fthres,
            pthres=fpfs_config.pthres,
            bound=fpfs_config.bound,
            noise_array=noise_array,
        )
        del dtask

    mtask_s = FpfsMeasure(
        mag_zero=mag_zero,
        psf_array=psf_array,
        pixel_scale=pixel_scale,
        sigma_arcsec=fpfs_config.sigma_arcsec,
        klim_thres=fpfs_config.klim_thres,
        nord=fpfs_config.nord,
        det_nrot=-1,
    )
    src_s = mtask_s.run(
        gal_array=gal_array,
        det=coords,
        noise_array=noise_array,
    )
    del mtask_s

    mtask_d = FpfsMeasure(
        mag_zero=mag_zero,
        psf_array=psf_array,
        pixel_scale=pixel_scale,
        sigma_arcsec=fpfs_config.sigma_arcsec,
        klim_thres=fpfs_config.klim_thres,
        nord=-1,
        det_nrot=fpfs_config.det_nrot,
    )
    src_d = mtask_d.run(
        gal_array=gal_array,
        det=coords,
        noise_array=noise_array,
    )
    del mtask_d

    # Catalog
    cat_task = CatalogTask(
        nord=fpfs_config.nord,
        det_nrot=fpfs_config.det_nrot,
        cov_matrix=cov_matrix,
    )
    cat_task.update_parameters(
        snr_min=fpfs_config.snr_min,
        r2_min=fpfs_config.r2_min,
        c0=fpfs_config.c0,
        pthres=fpfs_config.pthres,
    )
    out = cat_task.run(cat1=src_d, cat2=src_s)
    return out
