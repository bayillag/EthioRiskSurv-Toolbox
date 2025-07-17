# -*- coding: utf-8 -*-

import os
import unittest
import tempfile
import shutil

# This setup is needed to run QGIS processing algorithms in a standalone script
from qgis.core import QgsApplication, QgsVectorLayer, QgsRasterLayer, QgsProject

# Import the class we want to test
from ..plugin.risk_analyzer import RiskAnalyzer

# Set up the path to the fixtures directory
# This assumes the test is run from the project's root directory
# e.g., python3 -m unittest ethiosurv_risk_toolbox.tests.test_risk_analyzer
TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'fixtures')

class TestRiskAnalyzer(unittest.TestCase):
    """Test suite for the RiskAnalyzer class."""

    @classmethod
    def setUpClass(cls):
        """
        Set up the QGIS application. This is run once for the entire test class.
        """
        # The second argument to QgsApplication is False to indicate we're not running a GUI.
        cls.qgs = QgsApplication([], False)
        cls.qgs.initQgis()

        # Create a temporary directory for test outputs
        cls.temp_dir = tempfile.mkdtemp()
        
        # Create a temporary QGIS project instance to hold layers
        cls.project = QgsProject.instance()
        
        # Load fixture data
        cls.study_area_path = os.path.join(TEST_DATA_PATH, 'test_study_area.shp') # You should create this
        cls.points_path = os.path.join(TEST_DATA_PATH, 'test_points.shp')
        cls.raster_path = os.path.join(TEST_DATA_PATH, 'test_risk_map.tif')

        # Check if fixture data exists
        if not os.path.exists(cls.study_area_path) or not os.path.exists(cls.points_path) or not os.path.exists(cls.raster_path):
            raise FileNotFoundError("Make sure test fixture data (test_study_area.shp, test_points.shp, test_risk_map.tif) exists in tests/fixtures/")

    @classmethod
    def tearDownClass(cls):
        """
        Clean up the QGIS application and temporary files. This is run once after all tests.
        """
        cls.qgs.exitQgis()
        shutil.rmtree(cls.temp_dir) # Remove the temporary directory and all its contents

    def setUp(self):
        """

        Set up for each individual test method.
        This method creates fresh layer objects for each test to ensure they are independent.
        """
        self.study_area_layer = QgsVectorLayer(self.study_area_path, "study_area", "ogr")
        self.points_layer = QgsVectorLayer(self.points_path, "points", "ogr")
        self.raster_layer = QgsRasterLayer(self.raster_path, "raster")
        self.assertTrue(self.study_area_layer.isValid(), "Test study area layer failed to load.")
        self.assertTrue(self.points_layer.isValid(), "Test points layer failed to load.")
        self.assertTrue(self.raster_layer.isValid(), "Test raster layer failed to load.")
        
        # Add layers to the temporary project so processing algorithms can find them by name if needed
        self.project.addMapLayers([self.study_area_layer, self.points_layer, self.raster_layer])

    def tearDown(self):
        """
        Clean up after each test method.
        """
        self.project.clear() # Clear all layers from the project instance


    def test_risk_analyzer_run(self):
        """
        Test the main run() method of the RiskAnalyzer.
        """
        print("\n--- Running test_risk_analyzer_run ---")

        # 1. Define the inputs for the analyzer
        risk_factors = [
            {
                'layer': self.raster_layer,
                'weight': 8,
                'correlation': 'Higher values = Higher Risk'
            },
            {
                'layer': self.points_layer, # A vector layer (proximity)
                'weight': 10,
                'correlation': 'Lower values = Higher Risk'
            }
        ]
        resolution = 1000  # meters
        project_name = "Test_Analysis"

        # 2. Instantiate the analyzer
        analyzer = RiskAnalyzer(self.study_area_layer, risk_factors, resolution, project_name)
        
        # Override the project home path to use our temporary directory
        analyzer.project.setHomePath(self.temp_dir)

        # 3. Run the analysis
        success, final_risk_map = analyzer.run()

        # 4. Assert the results
        self.assertTrue(success, "RiskAnalyzer.run() should return success=True.")
        self.assertIsNotNone(final_risk_map, "RiskAnalyzer.run() should return a layer object.")
        self.assertIsInstance(final_risk_map, QgsRasterLayer, "The output should be a QgsRasterLayer.")
        self.assertTrue(final_risk_map.isValid(), "The final risk map layer should be valid.")

        # Check if the output file was actually created on disk
        expected_output_path = os.path.join(self.temp_dir, "Test_Analysis_RiskMap_Clipped.tif")
        self.assertTrue(os.path.exists(expected_output_path), f"Expected output file not found at {expected_output_path}")

        print("--- Test completed successfully ---")


if __name__ == '__main__':
    # This allows you to run the test script directly
    unittest.main()