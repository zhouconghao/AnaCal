#include <cmath>

namespace imath {

double ssfunc1(double x, double mu, double sigma) {
    auto _func = [](double t) -> double {
        return -2.0 * t * t * t + 3 * t * t;
    };

    double t = (x - mu) / (sigma * 2.0) + 0.5;
    if (t < 0) return 0.0;
    else if (t <= 1) return _func(t);
    else return 1.0;
}

double ssfunc2(double x, double mu, double sigma) {
    auto _func = [](double t) -> double {
        return 6 * t * t * t * t * t - 15 * t * t * t * t + 10 * t * t * t;
    };

    double t = (x - mu) / (sigma * 2.0) + 0.5;
    if (t < 0) return 0.0;
    else if (t <= 1) return _func(t);
    else return 1.0;
}

double sigmoid(double x, double mu, double sigma) {
    double t = (x - mu) / sigma;
    return 1.0 / (1.0 + std::exp(-t));
}

}
