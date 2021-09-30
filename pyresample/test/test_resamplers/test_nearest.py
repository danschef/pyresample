#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2021 Pyresample developers
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
"""Tests for the 'nearest' resampler."""

from unittest import mock

import dask.array as da
import numpy as np
import pytest
import xarray as xr
from pytest_lazyfixture import lazy_fixture

from pyresample.future.geometry import AreaDefinition, SwathDefinition
from pyresample.future.resamplers import NearestNeighborResampler
from pyresample.test.utils import assert_maximum_dask_computes


class TestNearestNeighborResampler:
    """Test the NearestNeighborResampler class."""

    def test_nearest_swath_1d_mask_to_grid_1n(
            self,
            swath_def_1d_xarray_dask, data_1d_float32_xarray_dask, coord_def_2d_float32_dask):
        """Test 1D swath definition to 2D grid definition; 1 neighbor."""
        resampler = NearestNeighborResampler(swath_def_1d_xarray_dask, coord_def_2d_float32_dask)
        res = resampler.resample(data_1d_float32_xarray_dask,
                                 mask_area=data_1d_float32_xarray_dask.isnull(),
                                 radius_of_influence=100000)
        assert isinstance(res, xr.DataArray)
        assert isinstance(res.data, da.Array)
        actual = res.values
        expected = np.array([
            [1., 2., 2.],
            [1., 2., 2.],
            [1., np.nan, 2.],
            [1., 2., 2.],
        ])
        np.testing.assert_allclose(actual, expected)

    def test_nearest_type_preserve(self, swath_def_1d_xarray_dask, coord_def_2d_float32_dask):
        """Test 1D swath definition to 2D grid definition; 1 neighbor."""
        data = xr.DataArray(da.from_array(np.array([1, 2, 3]),
                                          chunks=5),
                            dims=('my_dim1',))

        resampler = NearestNeighborResampler(swath_def_1d_xarray_dask, coord_def_2d_float32_dask)
        res = resampler.resample(data, fill_value=255,
                                 radius_of_influence=100000)
        assert isinstance(res, xr.DataArray)
        assert isinstance(res.data, da.Array)
        actual = res.values
        expected = np.array([
            [1, 2, 2],
            [1, 2, 2],
            [1, 255, 2],
            [1, 2, 2],
        ])
        np.testing.assert_equal(actual, expected)

    def test_nearest_swath_2d_mask_to_area_1n(self, swath_def_2d_xarray_dask, data_2d_float32_xarray_dask,
                                              area_def_stere_target):
        """Test 2D swath definition to 2D area definition; 1 neighbor."""
        resampler = NearestNeighborResampler(
            swath_def_2d_xarray_dask, area_def_stere_target)
        res = resampler.resample(data_2d_float32_xarray_dask, radius_of_influence=50000)
        assert isinstance(res, xr.DataArray)
        assert isinstance(res.data, da.Array)
        res = res.values
        cross_sum = float(np.nansum(res))
        expected = 167913.0
        assert cross_sum == expected
        assert res.shape == resampler.target_geo_def.shape

    def test_nearest_area_2d_to_area_1n(self, area_def_stere_source, data_2d_float32_xarray_dask,
                                        area_def_stere_target):
        """Test 2D area definition to 2D area definition; 1 neighbor."""
        resampler = NearestNeighborResampler(
            area_def_stere_source, area_def_stere_target)
        with assert_maximum_dask_computes(0):
            resampler.precompute(radius_of_influence=50000)

        with assert_maximum_dask_computes(0):
            res = resampler.resample(data_2d_float32_xarray_dask, radius_of_influence=50000)
        assert isinstance(res, xr.DataArray)
        assert isinstance(res.data, da.Array)
        res = res.values
        cross_sum = float(np.nansum(res))
        expected = 303048.0
        assert cross_sum == expected
        assert res.shape == resampler.target_geo_def.shape

        data = data_2d_float32_xarray_dask.rename({'y': 'my_dim_y', 'x': 'my_dim_x'})
        pytest.raises(AssertionError, resampler.resample, data, radius_of_influence=50000)

    def test_nearest_area_2d_to_area_1n_no_roi(self, area_def_stere_source, data_2d_float32_xarray_dask,
                                               area_def_stere_target):
        """Test 2D area definition to 2D area definition; 1 neighbor, no radius of influence."""
        resampler = NearestNeighborResampler(
            area_def_stere_source, area_def_stere_target)
        resampler.precompute()

        res = resampler.resample(data_2d_float32_xarray_dask)
        assert isinstance(res, xr.DataArray)
        assert isinstance(res.data, da.Array)
        res = res.values
        cross_sum = float(np.nansum(res))
        expected = 952386.0
        assert cross_sum == expected
        assert res.shape == resampler.target_geo_def.shape

        # pretend the resolutions can't be determined
        with mock.patch.object(area_def_stere_source, 'geocentric_resolution') as sgr, \
                mock.patch.object(area_def_stere_target, 'geocentric_resolution') as dgr:
            sgr.side_effect = RuntimeError
            dgr.side_effect = RuntimeError
            resampler = NearestNeighborResampler(
                area_def_stere_source, area_def_stere_target)
            res = resampler.resample(data_2d_float32_xarray_dask)
            assert isinstance(res, xr.DataArray)
            assert isinstance(res.data, da.Array)
            res = res.values
            cross_sum = np.nansum(res)
            expected = 20666.0
            assert cross_sum == expected
            assert res.shape == resampler.target_geo_def.shape

        data = data_2d_float32_xarray_dask.rename({'y': 'my_dim_y', 'x': 'my_dim_x'})
        pytest.raises(AssertionError, resampler.resample, data)

    def test_nearest_area_2d_to_area_1n_3d_data(self, area_def_stere_source, data_3d_float32_xarray_dask,
                                                area_def_stere_target):
        """Test 2D area definition to 2D area definition; 1 neighbor, 3d data."""
        resampler = NearestNeighborResampler(
            area_def_stere_source, area_def_stere_target)
        resampler.precompute(radius_of_influence=50000)

        res = resampler.resample(data_3d_float32_xarray_dask, radius_of_influence=50000)
        assert isinstance(res, xr.DataArray)
        assert isinstance(res.data, da.Array)
        assert list(res.coords['bands']) == ['r', 'g', 'b']
        res = res.values
        cross_sum = float(np.nansum(res))
        expected = 909144.0
        assert cross_sum == expected
        assert res.shape[:2] == resampler.target_geo_def.shape

        data = data_3d_float32_xarray_dask.rename({'y': 'my_dim_y', 'x': 'my_dim_x'})
        pytest.raises(AssertionError, resampler.resample, data, radius_of_influence=50000)

    @pytest.mark.skipif(True, reason="Multiple neighbors not supported yet")
    def test_nearest_swath_1d_mask_to_grid_8n(
            self,
            swath_def_1d_xarray_dask,
            data_1d_float32_xarray_dask,
            coord_def_2d_dask
    ):
        """Test 1D swath definition to 2D grid definition; 8 neighbors."""
        resampler = NearestNeighborResampler(
            swath_def_1d_xarray_dask, coord_def_2d_dask)
        resampler.precompute(mask=data_1d_float32_xarray_dask.isnull(),
                             radius_of_influence=100000, neighbors=8)
        res = resampler.resample(data_1d_float32_xarray_dask)
        assert isinstance(res, xr.DataArray)
        assert isinstance(res.data, da.Array)
        # actual = res.values
        # expected =
        # np.testing.assert_allclose(actual, expected)


class TestInvalidUsageNearestNeighborResampler:
    """Test the resampler being given input that should raise an error.

    If a case here is removed because functionality is added to the resampler
    then a working case should be added above.

    """

    # @pytest.mark.parametrize("src_geom", [
    #     # lazy_fixture("swath_def_2d_numpy"),
    #     lazy_fixture("swath_def_2d_dask"),
    #     # lazy_fixture("swath_def_2d_xarray_numpy"),
    #     lazy_fixture("swath_def_2d_xarray_dask"),
    #     lazy_fixture("area_def_lcc_conus_1km"),
    # ])
    # @pytest.mark.parametrize("dst_geom", [
    #     # lazy_fixture("swath_def_2d_numpy"),
    #     lazy_fixture("swath_def_2d_dask"),
    #     # lazy_fixture("swath_def_2d_xarray_numpy"),
    #     lazy_fixture("swath_def_2d_xarray_dask"),
    #     lazy_fixture("area_def_lcc_conus_1km"),
    # ])
    # @pytest.mark.parametrize("input_data_type", [
    #     "numpy",
    # ])
    # def test_object_type_with_warnings(self, src_geom, dst_geom, input_data_type):
    #     """Test that providing certain input data causes a warning."""
    #     if input_data_type == "numpy":
    #         input_data = np.array(src_geom.shape, dtype=np.float32)
    #     else:
    #         raise NotImplementedError(f"Test does not understand input data type {input_data_type} yet.")
    #
    #     resampler = NearestNeighborResampler(src_geom, dst_geom)
    #     with warnings.catch_warnings(record=True) as w, assert_maximum_dask_computes(1):
    #         res = resampler.resample(input_data)
    #         assert type(res) is type(input_data)
    #     assert_warnings_contain(w, "will be converted")

    @pytest.mark.parametrize(
        "src_geom",
        [
            lazy_fixture("area_def_stere_source"),
            lazy_fixture("swath_def_2d_xarray_dask")
        ]
    )
    @pytest.mark.parametrize(
        ("match", "call_precompute"),
        [
            (".*data.*shape.*", False),
            (".*'mask'.*shape.*", True),
        ]
    )
    def test_inconsistent_input_shapes(self, src_geom, match, call_precompute,
                                       area_def_stere_target, data_2d_float32_xarray_dask):
        """Test that geometry and data of the same size but different size still error."""
        # transpose the source geometries
        if isinstance(src_geom, AreaDefinition):
            src_geom = AreaDefinition(
                src_geom.area_id, src_geom.description, src_geom.proj_id,
                src_geom.crs, src_geom.height, src_geom.width, src_geom.area_extent,
            )
        else:
            src_geom = SwathDefinition(
                src_geom.lons.T, src_geom.lats.T,
            )
        resampler = NearestNeighborResampler(src_geom, area_def_stere_target)
        with pytest.raises(ValueError, match=match):
            if call_precompute:
                resampler.precompute(mask=data_2d_float32_xarray_dask.notnull())
            else:
                resampler.resample(data_2d_float32_xarray_dask)
