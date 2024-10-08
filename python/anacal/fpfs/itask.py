# Image Tasks of Shapelet Based Measurements
#
# python lib
import numpy as np
from numpy.typing import NDArray

from . import BasePsf, FpfsImage, Image, mask_galaxy_image
from .base import ImgBase
from .table import Catalog, Covariance

npix_patch = 256
npix_overlap = 64
npix_default = 64


class FpfsNoiseCov(ImgBase):
    """A class to measure FPFS noise covariance of basis modes

    Args:
    psf_array (NDArray): an average PSF image used to initialize the task
    pixel_scale (float): pixel scale in arcsec
    sigma_arcsec (float): Shapelet kernel size
    norder (int): the highest order of Shapelets radial components [default: 4]
    det_nrot (int): number of rotation in the detection kernel
    kmax_thres (float): the tuncation threshold on Gaussian [default: 1e-20]
    mag_zero (float): magnitude zero point [default 30]

    NOTE: The current version of Anacal.Fpfs only uses two elements of the
    covariance matrix. The full matrix will be useful in the future.
    """

    def __init__(
        self,
        psf_array: NDArray,
        pixel_scale: float,
        sigma_arcsec: float,
        norder: int = 4,
        det_nrot: int = 4,
        kmax_thres: float = 1e-20,
        mag_zero: float = 30.0,
    ) -> None:
        super().__init__(
            npix=npix_default,
            psf_array=psf_array,
            pixel_scale=pixel_scale,
            sigma_arcsec=sigma_arcsec,
            norder=norder,
            det_nrot=det_nrot,
            kmax_thres=kmax_thres,
            mag_zero=mag_zero,
        )

        # Preparing PSF
        psf_f = np.fft.rfft2(psf_array)
        self.psf_pow = (np.abs(psf_f) ** 2.0).astype(np.float64)
        self.prepare_fpfs_bases()
        return

    def measure(
        self, variance: float, noise_pf: NDArray | None = None
    ) -> Covariance:
        """Estimates covariance of measurement error

        Args:
        variance (float): Noise variance
        noise_pf (NDArray | None): Power spectrum (assuming homogeneous) of
        noise

        Return:
        (Covariance): covariance matrix of FPFS basis modes
        """
        if noise_pf is not None:
            if noise_pf.shape == (self.npix, self.npix // 2 + 1):
                # rfft
                noise_pf = np.array(noise_pf, dtype=np.float64)
            elif noise_pf.shape == (self.npix, self.npix):
                # fft
                noise_pf = np.fft.ifftshift(noise_pf)
                noise_pf = np.array(
                    noise_pf[:, : self.npix // 2 + 1], dtype=np.float64
                )
            else:
                raise ValueError("noise power not in correct shape")
        else:
            ss = (self.npix, self.npix // 2 + 1)
            noise_pf = np.ones(ss)
        norm_factor = variance * self.npix**2.0 / noise_pf[0, 0]
        noise_pf = noise_pf * norm_factor

        img_obj = Image(nx=self.npix, ny=self.npix, scale=self.pixel_scale)
        img_obj.set_f(noise_pf)
        img_obj.deconvolve(
            psf_image=self.psf_pow,
            klim=self.kmax / self.pixel_scale,
        )
        noise_pf_deconv = img_obj.draw_f().real
        del img_obj

        _w = np.ones(self.psf_pow.shape) * 2.0
        _w[:, 0] = 1.0
        _w[:, -1] = 1.0
        cov_elems = (
            np.tensordot(
                self.bfunc * (_w * noise_pf_deconv)[np.newaxis, :, :],
                np.conjugate(self.bfunc),
                axes=((1, 2), (1, 2)),
            ).real
            / self.pixel_scale**4.0
        )
        return Covariance(
            array=cov_elems,
            norder=self.norder,
            det_nrot=self.det_nrot,
            pixel_scale=self.pixel_scale,
            sigma_arcsec=self.sigma_arcsec,
            mag_zero=self.mag_zero,
        )


class FpfsDetect(ImgBase):
    """A base class for measurement

    Args:
    pixel_scale (float): pixel scale in arcsec
    sigma_arcsec (float): Gaussian kernel size
    cov_matrix (Covariance): covariance matrix of Fpfs basis modes
    norder (int): the highest order of Shapelets radial components [default: 4]
    det_nrot (int): number of rotation in the detection kernel [default: 8]
    kmax (float | None): maximum k
    psf_array (NDArray): an average PSF image used to initialize the task
    kmax_thres (float): the tuncation threshold on Gaussian [default: 1e-20]
    bound (int): minimum distance to boundary [default: 0]
    mag_zero (float): magnitude zero point [default: 30]
    """

    def __init__(
        self,
        cov_matrix: Covariance,
        pixel_scale: float,
        sigma_arcsec: float,
        norder: int = 4,
        det_nrot: int = 4,
        kmax: float | None = None,
        psf_array: NDArray | None = None,
        kmax_thres: float = 1e-20,
        bound: int = 0,
        mag_zero: float = 30.0,
    ) -> None:
        super().__init__(
            npix=npix_default,
            sigma_arcsec=sigma_arcsec,
            pixel_scale=pixel_scale,
            norder=norder,
            det_nrot=det_nrot,
            kmax=kmax,
            psf_array=psf_array,
            kmax_thres=kmax_thres,
            mag_zero=mag_zero,
        )

        self.dtask = FpfsImage(
            nx=npix_patch,
            ny=npix_patch,
            scale=self.pixel_scale,
            sigma_arcsec=self.sigma_arcsec,
            klim=self.kmax / self.pixel_scale,
            psf_array=psf_array,
            use_estimate=True,
            npix_overlap=npix_overlap,
            bound=bound,
        )

        assert self.mag_zero == cov_matrix.mag_zero
        self.std_m00 = cov_matrix.std_m00
        self.std_v = cov_matrix.std_v
        return

    def run(
        self,
        gal_array: NDArray,
        fthres: float,
        pthres: float,
        noise_array: NDArray | None = None,
        mask_array: NDArray | None = None,
        star_cat: NDArray | None = None,
    ) -> NDArray:
        """This function detects galaxy from image

        Args:
        gal_array (NDArray): galaxy image data
        fthres (float): flux threshold
        pthres (float): peak threshold
        noise_array (NDArray|None): pure noise image
        mask_array (NDArray|None): mask image
        star_cat (NDArray|None): bright star catalog

        Returns:
        (NDArray): galaxy detection catalog
        """

        if mask_array is not None:
            # Set the value inside star mask to zero
            mask_galaxy_image(gal_array, mask_array, True, star_cat)
            if noise_array is not None:
                # Also do it for pure noise image
                mask_galaxy_image(noise_array, mask_array, False, star_cat)

        # ny, nx = gal_array.shape
        # assert ny == self.ny
        # assert nx == self.nx
        return self.dtask.detect_source(
            gal_array=gal_array,
            fthres=fthres,
            pthres=pthres,
            std_m00=self.std_m00 * self.pixel_scale**2.0,
            std_v=self.std_v * self.pixel_scale**2.0,
            noise_array=noise_array,
            mask_array=mask_array,
        )


class FpfsMeasure(ImgBase):
    """A base class for measurement

    Args:
    pixel_scale (float): pixel scale in arcsec
    sigma_arcsec (float): Shapelet kernel size
    norder (int): the highest order of Shapelets radial components [default: 4]
    det_nrot (int): number of rotation in the detection kernel
    kmax (float | None): maximum k
    psf_array (NDArray | None): an average PSF image used to initialize the task
    kmax_thres (float): the tuncation threshold on Gaussian [default: 1e-20]
    mag_zero (float): magnitude zero point [default: 30.0]
    """

    def __init__(
        self,
        pixel_scale: float,
        sigma_arcsec: float,
        norder: int = 4,
        det_nrot: int = 4,
        kmax: float | None = None,
        psf_array: NDArray | None = None,
        kmax_thres: float = 1e-20,
        mag_zero: float = 30.0,
    ) -> None:
        super().__init__(
            npix=npix_default,
            pixel_scale=pixel_scale,
            sigma_arcsec=sigma_arcsec,
            norder=norder,
            det_nrot=det_nrot,
            kmax=kmax,
            psf_array=psf_array,
            kmax_thres=kmax_thres,
            mag_zero=mag_zero,
        )
        self.mtask = FpfsImage(
            nx=self.npix,
            ny=self.npix,
            scale=self.pixel_scale,
            sigma_arcsec=self.sigma_arcsec,
            klim=self.kmax / self.pixel_scale,
            psf_array=psf_array,
            use_estimate=True,
        )
        self.prepare_fpfs_bases()

        self.bfunc_use = np.transpose(self.bfunc, (1, 2, 0))
        return

    def run_single_psf(
        self,
        gal_array: NDArray,
        psf_array: NDArray,
        noise_array: NDArray | None = None,
        det: NDArray | None = None,
    ) -> tuple[NDArray, NDArray | None]:
        """This function measure galaxy shapes at the position of the detection
        using PSF image data

        Args:
        gal_array (NDArray): galaxy image data
        psf_array (NDArray): psf image data
        noise_array (NDArray | None): noise image data [default: None]
        det (list|None): detection catalog

        Returns:
        src_g (NDArray): source measurement catalog
        src_n (NDArray): noise measurement catalog
        """
        src_g = self.mtask.measure_source(
            gal_array=gal_array,
            filter_image=self.bfunc_use,
            psf_array=psf_array,
            det=det,
            do_rotate=False,
        )
        if noise_array is not None:
            src_n = self.mtask.measure_source(
                gal_array=noise_array,
                filter_image=self.bfunc_use,
                psf_array=psf_array,
                det=det,
                do_rotate=True,
            )
            src_g = src_g + src_n
        else:
            src_n = None
        return src_g, src_n

    def run_spacial_psf(
        self,
        gal_array: NDArray,
        psf_obj: BasePsf,
        noise_array: NDArray | None = None,
        det: NDArray | None = None,
    ) -> tuple[NDArray, NDArray | None]:
        """This function measure galaxy shapes at the position of the detection
        using PSF model with spacial variation

        Args:
        gal_array (NDArray): galaxy image data
        psf_model (BasePsf): psf image data
        noise_array (NDArray | None): noise image data [default: None]
        det (list|None): detection catalog

        Returns:
        src_g (NDArray): source measurement catalog
        src_n (NDArray): noise measurement catalog
        """
        src_g = self.mtask.measure_source(
            gal_array=gal_array,
            filter_image=self.bfunc_use,
            psf_obj=psf_obj,
            det=det,
            do_rotate=False,
        )
        if noise_array is not None:
            src_n = self.mtask.measure_source(
                gal_array=noise_array,
                filter_image=self.bfunc_use,
                psf_obj=psf_obj,
                det=det,
                do_rotate=True,
            )
            src_g = src_g + src_n
        else:
            src_n = None
        return src_g, src_n

    def run(
        self,
        gal_array: NDArray,
        psf: BasePsf | NDArray,
        noise_array: NDArray | None = None,
        det: NDArray | None = None,
    ) -> Catalog:
        """This function measure galaxy shapes at the position of the detection

        Args:
        gal_array (NDArray): galaxy image data
        psf (BasePsf | NDArray): psf image data or psf model
        noise_array (NDArray | None): noise image data [default: None]
        det (list|None): detection catalog

        Returns:
        (NDArray): galaxy measurement catalog
        """
        if isinstance(psf, np.ndarray):
            src_g, src_n = self.run_single_psf(
                gal_array=gal_array,
                psf_array=psf,
                noise_array=noise_array,
                det=det,
            )
        elif isinstance(psf, BasePsf) and psf.crun:
            src_g, src_n = self.run_spacial_psf(
                gal_array=gal_array,
                psf_obj=psf,
                noise_array=noise_array,
                det=det,
            )
        else:
            raise RuntimeError("psf does not have a correct type")
        return Catalog(
            array=src_g,
            noise=src_n,
            mag_zero=self.mag_zero,
            norder=self.norder,
            det_nrot=self.det_nrot,
            pixel_scale=self.pixel_scale,
            sigma_arcsec=self.sigma_arcsec,
        )
