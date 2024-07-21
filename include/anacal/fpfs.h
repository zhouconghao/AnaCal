#ifndef ANACAL_FPFS_H
#define ANACAL_FPFS_H

#include "image.h"
#include "psf.h"
#include "math.h"
#include "mask.h"

namespace anacal {
    inline constexpr double fpfs_cut_sigma_ratio = 1.6;
    inline constexpr double fpfs_det_sigma2 = 0.04;
    inline constexpr double fpfs_pnr = 0.8;

    class FpfsImage {
    private:
        // Preventing copy (implement these if you need copy semantics)
        FpfsImage(const FpfsImage&) = delete;
        FpfsImage& operator=(const FpfsImage&) = delete;
        Image cimg;
        double fft_ratio;
        const py::array_t<double> psf_array;
    public:
        double scale = 1.0;
        double sigma_arcsec;
        double klim;
        double sigma_f;
        int nx, ny;

        FpfsImage(
            int nx,
            int ny,
            double scale,
            double sigma_arcsec,
            double klim,
            const py::array_t<double>& psf_array,
            bool use_estimate=true
        );

        py::array_t<double>
        smooth_image(
            const py::array_t<double>& gal_array,
            bool do_rotate,
            int x,
            int y
        );

        py::array_t<double>
        smooth_image(
            const py::array_t<double>& gal_array,
            const std::optional<py::array_t<double>>& noise_array,
            int x,
            int y
        );

        py::array_t<FpfsPeaks>
        find_peak(
            const py::array_t<double>& gal_conv,
            double fthres,
            double pthres,
            double std_m00,
            double std_v,
            int bound
        );

        py::array_t<FpfsPeaks>
        detect_source(
            py::array_t<double>& gal_array,
            double fthres,
            double pthres,
            double std_m00,
            double std_v,
            int bound,
            const std::optional<py::array_t<double>>& noise_array=std::nullopt,
            const std::optional<py::array_t<int16_t>>& mask_array=std::nullopt
        );

        py::array_t<double>
        measure_source(
            const py::array_t<double>& gal_array,
            const py::array_t<std::complex<double>>& filter_image,
            const std::optional<py::array_t<double>>& psf_array=std::nullopt,
            const std::optional<py::array_t<FpfsPeaks>>& det=std::nullopt,
            bool do_rotate=false
        );

        py::array_t<double>
        measure_source(
            const py::array_t<double>& gal_array,
            const py::array_t<std::complex<double>>& filter_image,
            const BasePsf& psf_obj,
            const std::optional<py::array_t<FpfsPeaks>>& det=std::nullopt,
            bool do_rotate=false
        );

        FpfsImage(FpfsImage&& other) noexcept = default;
        FpfsImage& operator=(FpfsImage&& other) noexcept = default;

        ~FpfsImage();
    };

    void pyExportFpfs(py::module& m);
}

#endif // ANACAL_FPFS_H
