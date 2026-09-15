"""Sprint 0 gate check: the core toolchain imports and DEVSIM's solver loads."""

import numpy
import scipy
import pandas
import matplotlib


def test_devsim_imports():
    import devsim

    assert hasattr(devsim, "solve")
    assert hasattr(devsim, "create_device")


def test_scientific_stack_imports():
    assert numpy.__version__
    assert scipy.__version__
    assert pandas.__version__
    assert matplotlib.__version__
