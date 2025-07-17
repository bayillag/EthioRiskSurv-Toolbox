# -*- coding: utf-8 -*-

import unittest
import math

# This setup is needed to run QGIS processing algorithms in a standalone script
from qgis.core import QgsApplication, QgsVectorLayer, QgsFields, QgsField, QgsFeature, QgsGeometry, QgsPointXY
from PyQt5.QtCore import QVariant

# Import the class we want to test
from ..plugin.cost_evaluator import CostEvaluator

class TestCostEvaluator(unittest.TestCase):
    """Test suite for the CostEvaluator class."""

    @classmethod
    def setUpClass(cls):
        """
        Set up the QGIS application. Run once for the entire test class.
        """
        cls.qgs = QgsApplication([], False)
        cls.qgs.initQgis()

    @classmethod
    def tearDownClass(cls):
        """
        Clean up the QGIS application. Run once after all tests.
        """
        cls.qgs.exitQgis()

    def setUp(self):
        """
        Set up for each individual test method.
        This method creates a fresh in-memory layer for each test.
        """
        # Create an in-memory point layer with a specific number of features
        self.num_samples = 120
        self.sampling_layer = QgsVectorLayer("Point?crs=epsg:4326", "TestSamplingPlan", "memory")
        provider = self.sampling_layer.dataProvider()
        
        features = []
        for i in range(self.num_samples):
            feat = QgsFeature()
            # The actual point location doesn't matter for this test,
            # unless we were testing the advanced road network logic.
            # We will test the simpler HQ distance calculation.
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(i, i)))
            features.append(feat)
        
        provider.addFeatures(features)
        self.assertEqual(self.sampling_layer.featureCount(), self.num_samples)
        
        # Define a standard set of cost parameters for testing
        self.cost_params = {
            'cost_per_sample': 500,        # 500 ETB per sample
            'cost_per_diem': 1000,         # 1000 ETB per day per person
            'team_size': 2,                # 2 people per team
            'samples_per_day': 40,         # 40 samples collected per day by one team
            'cost_per_km': 20,             # 20 ETB per km
            'hq_point': QgsGeometry.fromPointXY(QgsPointXY(0, 0)) # HQ at origin
        }

    def test_calculate_total_cost(self):
        """
        Test the main calculate_total_cost() method with predictable inputs.
        """
        print("\n--- Running test_calculate_total_cost ---")

        # 1. Instantiate the evaluator
        evaluator = CostEvaluator(self.sampling_layer, self.cost_params)

        # 2. Run the calculation
        results = evaluator.calculate_total_cost()

        # 3. Assert the results based on our known inputs
        self.assertIsNotNone(results, "The result dictionary should not be None.")

        # --- A. Verify Fixed Costs ---
        # 120 samples * 500 ETB/sample = 60,000 ETB
        expected_fixed_costs = 120 * 500
        self.assertEqual(results['breakdown']['fixed_costs'], expected_fixed_costs)
        print(f"  - Fixed Costs OK: {expected_fixed_costs}")

        # --- B. Verify Personnel Costs ---
        # 120 samples / 40 samples/day = 3 days
        # 3 days * 2 people/team * 1000 ETB/day/person = 6,000 ETB
        expected_days = math.ceil(120 / 40)
        self.assertEqual(expected_days, 3)
        expected_personnel_costs = 3 * 2 * 1000
        self.assertEqual(results['breakdown']['personnel_costs'], expected_personnel_costs)
        print(f"  - Personnel Costs OK: {expected_personnel_costs}")
        
        # --- C. Verify Logistics Costs ---
        # This is an approximation as QgsDistanceArea is complex,
        # but we can check if it's a plausible number.
        # For this test, we'll just check that it's a positive number,
        # as the exact value depends on the ellipsoid and CRS math.
        self.assertGreater(results['breakdown']['logistics_costs'], 0)
        print(f"  - Logistics Costs OK (is positive): {results['breakdown']['logistics_costs']:.2f}")

        # --- D. Verify Total Cost ---
        expected_total_cost = expected_fixed_costs + expected_personnel_costs + results['breakdown']['logistics_costs']
        self.assertAlmostEqual(results['total_cost'], expected_total_cost, places=2)
        print(f"  - Total Cost OK: {results['total_cost']:.2f}")
        
        # --- E. Verify Cost per Sample ---
        expected_cost_per_sample = expected_total_cost / 120
        self.assertAlmostEqual(results['cost_per_sample'], expected_cost_per_sample, places=2)
        print(f"  - Cost per Sample OK: {results['cost_per_sample']:.2f}")

    def test_zero_samples(self):
        """
        Test the edge case where the input layer has no features.
        """
        print("\n--- Running test_zero_samples ---")
        
        # Create an empty layer
        empty_layer = QgsVectorLayer("Point?crs=epsg:4326", "EmptyPlan", "memory")
        self.assertEqual(empty_layer.featureCount(), 0)

        # Instantiate and run
        evaluator = CostEvaluator(empty_layer, self.cost_params)
        results = evaluator.calculate_total_cost()

        # The method should gracefully return None
        self.assertIsNone(results, "Evaluator should return None for a layer with zero features.")
        print("  - Zero samples case handled correctly.")


if __name__ == '__main__':
    unittest.main()