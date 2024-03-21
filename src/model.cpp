#include "model.h"

// Gaussian Profile
Gaussian::Gaussian(double sigma) : sigma(sigma) {
    _p0 = 1.0 / (2 * sigma * sigma);
}
std::complex<double>
Gaussian::fValue(double kx, double ky) const {
    double rpart = std::exp(-(kx*kx + ky*ky) * _p0 );
    return std::complex<double>(rpart, 0.0);
}

// Gaussian Tophat
GaussianTopHat::GaussianTopHat(double d, double sigma) : d(d), sigma(sigma) {
    _p0 = 1.0 / (std::sqrt(2) * sigma);
}
std::complex<double>
GaussianTopHat::fValue(double kx, double ky) const {
    double factorX = std::erf((kx + d) * _p0) - std::erf((kx - d) * _p0);
    double factorY = std::erf((ky + d) * _p0) - std::erf((ky - d) * _p0);
    return std::complex<double>(factorX * factorY * 0.25, 0.0);
}

py::array_t<std::complex<double>>
BaseFunc::draw(double scale, int nx, int ny) const {
    // Grid dimensions
    int kx_length = nx / 2 + 1;
    int ky_length = ny;

    // Prepare output array
    auto result = py::array_t<std::complex<double>>({ky_length, kx_length});
    auto r = result.mutable_unchecked<2>(); // Accessor

    double dkx = 2.0 * M_PI / nx / scale;
    double dky = 2.0 * M_PI / ny / scale;
    int ny2 = ny / 2;
    for (int iy = 0; iy < ky_length; ++iy) {
        double ky = (iy < ny2) ? iy * dky : (iy - ny) * dky ;

        for (int ix = 0; ix < kx_length; ++ix) {
            double kx = ix * dkx;
            r(iy, ix) = apply(kx, ky);
        }
    }

    return result;
}


std::shared_ptr<BaseFunc>
multiply(
    std::shared_ptr<BaseFunc> f1,
    std::shared_ptr<BaseFunc> f2
) {
    return std::make_shared<MultipliedBaseFunc>(
        f1,
        f2
    );
}

std::shared_ptr<BaseFunc>
divide(
    std::shared_ptr<BaseFunc> numerator,
    std::shared_ptr<BaseFunc> denominator
) {
    return std::make_shared<DividedBaseFunc>(
        numerator, denominator
    );
}


PYBIND11_MODULE(model, m) {
    py::class_<BaseFunc, std::shared_ptr<BaseFunc>>(m, "BaseFunc")
        .def("apply", &BaseFunc::apply,
            "Returns the pre-distorted function value at kx, ky",
            py::arg("kx"), py::arg("ky")
        )
        .def("fValue", &BaseFunc::fValue,
            "Returns the distorted value at kx, ky",
            py::arg("kx"), py::arg("ky")
        )
        .def("set_transform", &BaseFunc::set_transform,
            "Sets the transform parameters",
            py::arg("theta"), py::arg("gamma1"), py::arg("gamma2")
        )
        .def("draw", &BaseFunc::draw,
            "draw the distorted function to ndarray",
            py::arg("scale"), py::arg("nx"), py::arg("ny")
        )
        .def("__mul__", [](
                const std::shared_ptr<BaseFunc>& a,
                const std::shared_ptr<BaseFunc>& b
            ) {
                return multiply(a, b);
            },
            py::is_operator()
        )
        .def("__truediv__", [](
                const std::shared_ptr<BaseFunc>& a,
                const std::shared_ptr<BaseFunc>& b
            ) {
                return divide(a, b);
            },
            py::is_operator()
        );

    py::class_<Gaussian, std::shared_ptr<Gaussian>, BaseFunc>(m, "Gaussian")
        .def(py::init<double>(),
            "Gaussian basis function",
            py::arg("sigma")
        );

    py::class_<GaussianTopHat, std::shared_ptr<GaussianTopHat>, BaseFunc>(m, "GaussianTopHat")
        .def(py::init<double, double>(),
            "Gaussian convolved with top-hat basis function",
            py::arg("d"), py::arg("sigma")
        );
}
