# -*- coding: utf-8 -*-

import unittest
import os
import tempfile
import shutil
import numpy as np

# This setup is needed to run QGIS processing algorithms in a standalone script
from qgis.core import (
    QgsApplication, QgsVectorLayer, QgsRasterLayer, QgsProject, QgsRectangle,
    QgsRasterFileWriter, QgsFields, QgsFeature, QgsGeometry, QgsPointXY
)
from gdal_utils import gdal_translate # Part of a standard QGIS install

# Import the class we want to test
from ..plugin.sampling_designer import SamplingDesigner

class TestSamplingDesigner(unittest.TestCase):
    """Test suite for the SamplingDesigner class."""

    @classmethod
    def setUpClass(cls):
        """Set up the QGIS application and a temporary directory."""
        cls.qgs = QgsApplication([], False)
        cls.qgs.initQgis()
        cls.temp_dir = tempfile.mkdtemp()
        cls.project = QgsProject.instance()

    @classmethod
    def tearDownClass(cls):
        """Clean up the QGIS application and temporary files."""
        cls.qgs.exitQgis()
        shutil.rmtree(cls.temp_dir)

    def setUp(self):
        """
        Set up for each individual test method.
        Creates a predictable risk raster and a study area polygon.
        """
        # --- Create a predictable 10x10 raster risk map (0-1 values) ---
        self.risk_raster_path = os.path.join(self.temp_dir, 'test_risk.tif')
        writer = QgsRasterFileWriter(self.risk_raster_path)
        writer.create(gdal_translate.GDT_Float32, 10, 10)
        # Create a gradient from left (0.0) to right (0.9)
        block = np.tile(np.arange(0, 1, 0.1), (10, 1)).astype(np.float32)
        writer.writeBlock(block, 1, 0, 0) # band, x, y
        # The writer object needs to be deleted to finalize the file
        del writer
        
        self.risk_raster = QgsRasterLayer(self.risk_raster_path, "Risk Map")
        self.assertTrue(self.risk_raster.isValid(), "Test risk raster failed to load.")
        
        # --- Create a study area polygon that matches the raster extent ---
        self.study_area_layer = QgsVectorLayer("Polygon?crs=epsg:4326", "Study Area", "memory")
        provider = self.study_area_layer.dataProvider()
        feat = QgsFeature()
        # The extent here is based on the default 1-degree cells of a new raster
        extent = QgsRectangle(0, 0, 10, 10)
        feat.setGeometry(QgsGeometry.fromWkt(extent.asWktPolygon()))
        provider.addFeatures([feat])
        
        self.assertTrue(self.study_area_layer.isValid(), "Test study area layer failed to load.")

        # Add layers to the project
        self.project.addMapLayers([self.risk_raster, self.study_area_layer])
        
        # --- Common test parameters ---
        self.output_name = "Test_Sampling_Points"
        self.num_samples = 50

    def tearDown(self):
        """Clean up after each test method."""
        self.project.clear()

    def test_generate_random_points(self):
        """Test the simple random sampling strategy."""
        print("\n--- Running test_generate_random_points ---")
        designer = SamplingDesigner(self.risk_raster, self.study_area_layer, self.output_name)
        result_layer = designer.generate_random_points(self.num_samples)
        
        self.assertIsNotNone(result_layer, "Should return a valid layer object.")
        self.assertIsInstance(result_layer, QgsVectorLayer)
        self.assertEqual(result_layer.featureCount(), self.num_samples, "Should generate the exact number of requested samples.")
        print("  - Random sampling OK.")

    def test_generate_targeted_points(self):
        """Test the targeted (risk-based) sampling strategy."""
        print("\n--- Running test_generate_targeted_points ---")
        # We will target the highest risk areas (right half of our raster, where values are >= 0.5)
        threshold = 0.5
        designer = SamplingDesigner(self.risk_raster, self.study_area_layer, self.output_name)
        result_layer = designer.generate_targeted_points(threshold, self.num_samples)
        
        self.assertIsNotNone(result_layer)
        self.assertEqual(result_layer.featureCount(), self.num_samples)

        # Verify that all points fall within the high-risk area
        for feature in result_layer.getFeatures():
            point = feature.geometry().asPoint()
            # In our 10x10 raster, x-coordinates from 5 to 10 correspond to risk >= 0.5
            self.assertGreaterEqual(point.x(), 5, "All targeted points should be in the high-risk zone (x >= 5).")
            
        print("  - Targeted sampling OK: all points are in the correct high-risk zone.")

    def test_generate_stratified_points(self):
        """Test the stratified sampling strategy."""
        print("\n--- Running test_generate_stratified_points ---")
        
        # --- First, create a classified raster (e.g., 2 strata: Low/High risk) ---
        # Low risk: 0.0 - 0.5 (stratum 1)
        # High risk: 0.5 - 1.0 (stratum 2)
        expr = f'("{self.risk_raster.name()}@1" < 0.5) * 1 + ("{self.risk_raster.name()}@1" >= 0.5) * 2'
        params = {'EXPRESSION': expr, 'LAYERS': [self.risk_raster], 'OUTPUT': 'memory:'}
        classified_raster = processing.run("qgis:rastercalculator", params)['OUTPUT']
        self.assertTrue(classified_raster.isValid())
        
        # --- Define the number of samples per stratum ---
        strata_counts = {
            1: 20, # 20 samples in the low-risk stratum
            2: 30  # 30 samples in the high-risk stratum
        }
        total_samples = sum(strata_counts.values())

        designer = SamplingDesigner(self.risk_raster, self.study_area_layer, self.output_name)
        result_layer = designer.generate_stratified_points(classified_raster, strata_counts)
        
        self.assertIsNotNone(result_layer)
        self.assertEqual(result_layer.featureCount(), total_samples)
        
        # --- Verify that points fall in their correct strata ---
        low_risk_count = 0
        high_risk_count = 0
        for feature in result_layer.getFeatures():
            point = feature.geometry().asPoint()
            if point.x() < 5:
                low_risk_count += 1
            else:
                high_risk_count += 1
        
        self.assertEqual(low_risk_count, strata_counts[1], "Should be exactly 20 points in the low-risk stratum.")
        self.assertEqual(high_risk_count, strata_counts[2], "Should be exactly 30 points in the high-risk stratum.")
        
        print("  - Stratified sampling OK: correct number of points in each stratum.")


if __name__ == '__main__':
    unittest.main()