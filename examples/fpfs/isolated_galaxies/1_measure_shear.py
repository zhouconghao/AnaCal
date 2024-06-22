import anacal
import galsim
import numpy as np

nstamp = 100
seed = 2
pixel_scale = 0.2
noise_variance = 0.23

noise_array = None

rcut = 32
ngrid = rcut * 2
force_detect = True

if not force_detect:
    coords = None
    buff = 15
else:
    # force detection at center
    indx = np.arange(ngrid // 2, ngrid * nstamp, ngrid)
    indy = np.arange(ngrid // 2, ngrid * nstamp, ngrid)
    ns = len(indx) * len(indy)
    inds = np.meshgrid(indy, indx, indexing="ij")
    yx = np.vstack([np.ravel(_) for _ in inds])
    buff = 0
    dtype = np.dtype(
        [
            ("y", np.int32),
            ("x", np.int32),
            ("is_peak", np.int32),
            ("mask_value", np.int32),
        ]
    )
    coords = np.empty(ns, dtype=dtype)
    coords["y"] = yx[0]
    coords["x"] = yx[1]
    coords["is_peak"] = np.ones(ns)
    coords["mask_value"] = np.zeros(ns)

fpfs_config = anacal.fpfs.FpfsConfig(
    force=force_detect,
    rcut=rcut,
    gmeasure=3,
)


psf_obj = galsim.Moffat(beta=3.5, fwhm=0.6, trunc=0.6 * 4.0)
psf_array = (
    psf_obj.shift(0.5 * pixel_scale, 0.5 * pixel_scale)
    .drawImage(nx=ngrid, ny=ngrid, scale=pixel_scale)
    .array
)
psf_array = psf_array[
    ngrid // 2 - rcut : ngrid // 2 + rcut,
    ngrid // 2 - rcut : ngrid // 2 + rcut,
]

outcomes = []
for gname in ["g2-1", "g2-0"]:
    gal_array = anacal.simulation.make_isolated_sim(
        gal_type="mixed",
        sim_method="fft",
        psf_obj=psf_obj,
        gname=gname,
        seed=seed,
        ny=ngrid * nstamp,
        nx=ngrid * nstamp,
        scale=pixel_scale,
        do_shift=False,
        buff=buff,
        nrot_per_gal=1,
    )[0]

    outcomes.append(
        anacal.fpfs.process_image(
            fpfs_config=fpfs_config,
            gal_array=gal_array,
            psf_array=psf_array,
            pixel_scale=pixel_scale,
            noise_variance=noise_variance,
            noise_array=noise_array,
            coords=coords,
        )
    )


print(
    (np.sum(outcomes[1]["e1"]) - np.sum(outcomes[0]["e1"]))
    / (np.sum(outcomes[1]["e1_g1"]) + np.sum(outcomes[0]["e1_g1"]))
)
print(
    (np.sum(outcomes[1]["e2"]) - np.sum(outcomes[0]["e2"]))
    / (np.sum(outcomes[1]["e2_g2"]) + np.sum(outcomes[0]["e2_g2"]))
)
