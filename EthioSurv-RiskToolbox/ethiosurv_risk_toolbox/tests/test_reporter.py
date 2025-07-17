# -*- coding: utf-8 -*-

import unittest
import os
import tempfile
import shutil
from datetime import datetime

# Import the class we want to test
# We need to adjust the path since we are in the tests directory
from ..plugin.reporter import Reporter

class TestReporter(unittest.TestCase):
    """Test suite for the Reporter class."""

    def setUp(self):
        """
        Set up for each individual test method.
        Creates a temporary directory and sample report data.
        """
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a dummy map image file for the report to reference
        self.dummy_image_path = os.path.join(self.temp_dir, 'test_map.png')
        with open(self.dummy_image_path, 'wb') as f:
            # Create a minimal, valid 1x1 pixel PNG image (transparent)
            f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc`\x18\x05\xa3`\x14\x8c\x02\x00\x00\x00\xc2\xa0\xf7Om\x00\x00\x00\x00IEND\xaeB`\x82')

        # Create a comprehensive, realistic set of report data
        self.report_data = {
            'report_title': 'FMD Surveillance Plan - Test Report',
            'report_author': 'Test Developer',
            'report_date': datetime.now().strftime("%Y-%m-%d"),
            'project_name': 'FMD Test Project',
            'objective': 'Prevalence Estimation',
            'study_area_name': 'Central Ethiopia Test Zone',
            'sampling_strategy': 'Stratified',
            'total_samples': 150,
            'snap_layer_name': 'population_kebeles',
            'map_image_path': self.dummy_image_path,
            'risk_factors': [
                {'name': 'Cattle Density', 'weight': 8, 'correlation': 'Higher values = Higher Risk'},
                {'name': 'Proximity to Markets', 'weight': 10, 'correlation': 'Lower values = Higher Risk'}
            ],
            'cost_scenarios': [
                ['Scenario A', 'Stratified', '150', '250000', '1667'],
                ['Scenario B', 'Random', '200', '310000', '1550']
            ],
            'total_cost': 250000.00
        }

    def tearDown(self):
        """
        Clean up after each test method by removing the temporary directory.
        """
        shutil.rmtree(self.temp_dir)

    def test_build_report(self):
        """
        Test the main build_report() method to ensure a PDF is created.
        """
        print("\n--- Running test_build_report ---")

        # 1. Define the output path for the PDF
        output_pdf_path = os.path.join(self.temp_dir, 'test_report.pdf')

        # 2. Instantiate the Reporter
        # We need to temporarily modify the path logic to find the templates
        # from the test script's location.
        reporter = Reporter(self.report_data)
        # Get the path to the 'ethiosurv_risk_toolbox' directory
        plugin_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        reporter.template_dir = os.path.join(plugin_root, 'templates')

        # 3. Run the report builder
        success = reporter.build_report(output_pdf_path)

        # 4. Assert the results
        self.assertTrue(success, "build_report() should return True on success.")
        
        # Check that the file was actually created
        self.assertTrue(os.path.exists(output_pdf_path), "The PDF file should exist at the output path.")
        
        # Check that the file is not empty
        self.assertGreater(os.path.getsize(output_pdf_path), 0, "The created PDF file should not be empty.")
        
        print(f"  - PDF report created successfully at: {output_pdf_path}")
        
    def test_build_report_missing_data(self):
        """
        Test that the reporter handles missing (but not critical) data gracefully.
        """
        print("\n--- Running test_build_report_missing_data ---")
        
        # Remove some non-essential data
        self.report_data.pop('cost_scenarios')
        self.report_data.pop('snap_layer_name')
        
        output_pdf_path = os.path.join(self.temp_dir, 'test_report_missing_data.pdf')
        
        reporter = Reporter(self.report_data)
        plugin_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        reporter.template_dir = os.path.join(plugin_root, 'templates')

        success = reporter.build_report(output_pdf_path)

        # The report should still build successfully, as the template handles missing keys.
        self.assertTrue(success, "build_report() should still succeed with optional data missing.")
        self.assertTrue(os.path.exists(output_pdf_path))
        self.assertGreater(os.path.getsize(output_pdf_path), 0)

        print("  - PDF report with missing optional data created successfully.")


if __name__ == '__main__':
    unittest.main()