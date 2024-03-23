#include "anacal.h"


namespace anacal {

Image::Image() {}

// Initialize the Convolution object with data array
void Image::initialize(
    int nx,
    int ny,
    double scale
) {
    this->nx = nx;
    this->ny = ny;
    this->scale = scale;

    // array
    norm_factor = 1.0 / nx / ny;
    ny2 = ny / 2;
    npixels = nx * ny;
    npixels_f = ny * (nx / 2 + 1);
    kx_length = nx / 2 + 1;
    ky_length = ny;
    dkx = 2.0 * M_PI / nx / scale;
    dky = 2.0 * M_PI / ny / scale;

    data_r = (double*) fftw_malloc(sizeof(double) * npixels);
    data_f = (fftw_complex*) fftw_malloc(sizeof(fftw_complex) * npixels_f);
    plan_forward = fftw_plan_dft_r2c_2d(ny, nx, data_r, data_f, FFTW_ESTIMATE);
    plan_backward = fftw_plan_dft_c2r_2d(ny, nx, data_f, data_r, FFTW_ESTIMATE);
    return;
}

void Image::set_r (
    const py::array_t<double>& input
) {
    auto r = input.unchecked<2>();
    for (ssize_t j = 0; j < ny; ++j) {
        for (ssize_t i = 0; i < nx; ++i) {
            data_r[j * nx + i] = r(j, i);
        }
    }
    return;
}


void Image::set_f(
    const py::array_t<std::complex<double>>& input
) {
    auto r = input.unchecked<2>();
    for (ssize_t j = 0; j < ky_length ; ++j) {
        for (ssize_t i = 0; i < kx_length ; ++i) {
            int index = j * kx_length + i;
            data_f[index][0] = r(j, i).real();
            data_f[index][1] = r(j, i).imag();
        }
    }
    return;
}

void Image::fft() {
    fftw_execute(plan_forward);
    return;
}

void
Image::ifft() {
    fftw_execute(plan_backward);
    return;
}

void Image::convolve(
    const Image& filter_image
){
    fftw_complex* r = filter_image.data_f;
    for (int iy = 0; iy < ky_length; ++iy) {
        for (int ix = 0; ix < kx_length; ++ix) {
            int index = iy * kx_length + ix;
            std::complex<double> val1(data_f[index][0], data_f[index][1]);
            std::complex<double> val2(r[index][0], r[index][1]);
            val1 = val1 * val2;
            data_f[index][0] = val1.real();
            data_f[index][1] = val1.imag();
        }
    }
}

void Image::convolve(
    const BaseModel& filter_model
){
    for (int iy = 0; iy < ky_length; ++iy) {
        double ky = (iy < ny2) ? iy * dky : (iy - ny) * dky ;
        for (int ix = 0; ix < kx_length; ++ix) {
            int index = iy * kx_length + ix;
            double kx = ix * dkx;
            std::complex<double> val(data_f[index][0], data_f[index][1]);
            std::complex<double> result = val * filter_model.apply(
                kx=kx, ky=ky
            );
            data_f[index][0] = result.real();
            data_f[index][1] = result.imag();
        }
    }
}

void Image::deconvolve(
    const Image& filter_image,
    const double klim
){
    fftw_complex* r = filter_image.data_f;
    for (int iy = 0; iy < ky_length; ++iy) {
        double ky = (iy < ny2) ? iy * dky : (iy - ny) * dky ;
        for (int ix = 0; ix < kx_length; ++ix) {
            int index = iy * kx_length + ix;
            double kx = ix * dkx;
            std::complex<double> val1(data_f[index][0], data_f[index][1]);
            std::complex<double> val2(r[index][0], r[index][1]);
            val1 = val1 / val2;
            data_f[index][0] = val1.real();
            data_f[index][1] = val1.imag();
        }
    }
}

void Image::deconvolve(
    const BaseModel& filter_model,
    const double klim
){
    for (int iy = 0; iy < ky_length; ++iy) {
        double ky = (iy < ny2) ? iy * dky : (iy - ny) * dky ;
        for (int ix = 0; ix < kx_length; ++ix) {
            int index = iy * kx_length + ix;
            double kx = ix * dkx;
            std::complex<double> val(data_f[index][0], data_f[index][1]);
            std::complex<double> result = val / filter_model.apply(
                kx=kx, ky=ky
            );
            data_f[index][0] = result.real();
            data_f[index][1] = result.imag();
        }
    }
}

py::array_t<std::complex<double>>
Image::draw_f() const {
    // Prepare data_fput array
    auto result = py::array_t<std::complex<double>>({ky_length, kx_length});
    auto r = result.mutable_unchecked<2>(); // Accessor
    for (ssize_t j = 0; j < ky_length ; ++j) {
        for (ssize_t i = 0; i < kx_length ; ++i) {
            int index = j * kx_length + i;
            std::complex<double> val(data_f[index][0], data_f[index][1]);
            r(j, i) = val;
        }
    }
    return result;
}

py::array_t<double>
Image::draw_r() const {
    auto result = py::array_t<double>({ny, nx});
    auto r = result.mutable_unchecked<2>();
    for (ssize_t j = 0; j < ny; ++j) {
        for (ssize_t i = 0; i < nx; ++i) {
            r(j, i) = data_r[j * nx + i] * norm_factor;
        }
    }
    return result;
}

void
Image::destroy() {
    if (plan_forward) {
        fftw_destroy_plan(plan_forward);
        fftw_destroy_plan(plan_backward);
        fftw_free(data_r);
        fftw_free(data_f);
        plan_forward = nullptr;
        plan_backward = nullptr;
        data_r = nullptr;
        data_f = nullptr;
    }
}

Image::~Image() {
    destroy();
}

void pyExportImage(py::module& m) {
    py::module_ image = m.def_submodule("image", "submodule for convolution");
    py::class_<Image>(image, "Image")
        .def(py::init<>())
        .def("initialize", &Image::initialize,
            "Initialize the Convolution object using an ndarray",
            py::arg("nx"), py::arg("ny"), py::arg("scale")
        )
        .def("set_r", &Image::set_r,
            "Sets up the image in configuration space",
            py::arg("input")
        )
        .def("set_f", &Image::set_f,
            "Sets up the image in Fourier space",
            py::arg("input")
        )
        .def("fft", &Image::fft,
            "Conducts forward Fourier Trasform"
        )
        .def("ifft", &Image::ifft,
            "Conducts backward Fourier Trasform"
        )
        .def("convolve",
            static_cast<void (Image::*)(const Image&)>(&Image::convolve),
            "Convolve method with image object",
            py::arg("filter_image")
        )
        .def("convolve",
            static_cast<void (Image::*)(const BaseModel&)>(&Image::convolve),
            "Convolve method with model object",
            py::arg("filter_model")
        )
        .def("deconvolve",
            static_cast<void (Image::*)(const Image&, double)>(&Image::deconvolve),
            "Deconvolve method with image object",
            py::arg("filter_image"),
            py::arg("klim")
        )
        .def("deconvolve",
            static_cast<void (Image::*)(const BaseModel&, double)>(&Image::deconvolve),
            "Deconvolve method with model object",
            py::arg("filter_model"),
            py::arg("klim")
        )
        .def("draw_r", &Image::draw_r,
            "This function draws the image in configuration space"
        )
        .def("draw_f", &Image::draw_f,
            "This function draws the image's real fft"
        )
        .def("destroy", &Image::destroy);
}

}
