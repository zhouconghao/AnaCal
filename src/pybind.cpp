#include "anacal.h"


namespace anacal {
    PYBIND11_MODULE(_anacal, m)
    {
        pyExportModel(m);
        pyExportImage(m);

    }
}
