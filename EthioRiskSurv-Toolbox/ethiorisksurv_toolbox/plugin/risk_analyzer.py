# -*- coding: utf-8 -*-

import os
import processing
from qgis.core import QgsMessageLog, Qgis, QgsVectorLayer, QgsRasterLayer, QgsProject, QgsProcessingContext, QgsProcessingFeedback, QgsRasterCalculator, QgsRasterCalculatorEntry
from ..utils.gis_utils import normalize_raster
from ..utils import logger

class RiskAnalyzer:
    """
    Handles all core logic for Module 1: Risk Analysis.
    """
    def __init__(self, study_area_layer, risk_factors, resolution, project_name):
        self.study_area_layer = study_area_layer
        self.risk_factors = risk_factors
        self.resolution = resolution
        self.project_name = project_name
        self.project = QgsProject.instance()
        self.output_layers = []

    def run(self):
        """Main execution method for risk analysis."""
        QgsMessageLog.logMessage("Starting risk analysis process.", "EthioRiskSurv-Toolbox", Qgis.Info)

        # --- 1. Validate Inputs ---
        if not self.study_area_layer or not self.study_area_layer.isValid():
            QgsMessageLog.logMessage("Invalid study area layer provided.", "EthioRiskSurv-Toolbox", Qgis.Critical)
            return False

        if not self.risk_factors:
            QgsMessageLog.logMessage("No risk factors provided.", "EthioRiskSurv-Toolbox", Qgis.Warning)
            return False
            
        # --- 2. Prepare environment for processing ---
        context = QgsProcessingContext()
        feedback = QgsProcessingFeedback()
        
        # --- 3. Process each risk factor ---
        processed_factors = []
        for factor in self.risk_factors:
            layer = factor['layer']
            weight = factor['weight']
            correlation = factor['correlation'] # 'Higher' or 'Lower'
            
            QgsMessageLog.logMessage(f"Processing factor: {layer.name()}", "EthioRiskSurv-Toolbox", Qgis.Info)
            
            # Temporary path for intermediate files
            temp_path = os.path.join(self.project.homePath(), f"temp_{layer.name().replace(' ', '_')}.tif")

            # A. If vector, convert to raster (proximity)
            if isinstance(layer, QgsVectorLayer):
                params = {
                    'INPUT': layer,
                    'UNITS': 0, # Pixels
                    'OUTPUT': temp_path
                }
                # Run proximity (raster distance) analysis
                processing.run("gdal:proximity", params, context=context, feedback=feedback)
                processed_layer = QgsRasterLayer(temp_path, f"prox_{layer.name()}")
            else:
                processed_layer = layer # It's already a raster

            if not processed_layer.isValid():
                QgsMessageLog.logMessage(f"Failed to process layer {layer.name()}", "EthioRiskSurv-Toolbox", Qgis.Critical)
                continue

            # B. Normalize the processed raster to 0-1
            norm_path = os.path.join(self.project.homePath(), f"norm_{processed_layer.name().replace(' ', '_')}.tif")
            normalized_layer = normalize_raster(processed_layer, norm_path)
            
            if not normalized_layer or not normalized_layer.isValid():
                QgsMessageLog.logMessage(f"Failed to normalize layer {processed_layer.name()}", "EthioRiskSurv-Toolbox", Qgis.Critical)
                continue
            
            # C. Invert if correlation is 'Lower values = Higher Risk'
            if correlation == 'Lower values = Higher Risk':
                inverted_path = os.path.join(self.project.homePath(), f"inv_{normalized_layer.name().replace(' ', '_')}.tif")
                entry = QgsRasterCalculatorEntry()
                entry.ref = 'norm@1'
                entry.raster = normalized_layer
                entry.bandNumber = 1
                calc = QgsRasterCalculator(f'1 - "{entry.ref}"', inverted_path, 'GTiff', normalized_layer.extent(), normalized_layer.width(), normalized_layer.height(), [entry])
                calc.processCalculation()
                final_processed_layer = QgsRasterLayer(inverted_path, f"final_{layer.name()}")
            else:
                final_processed_layer = normalized_layer

            processed_factors.append({'layer': final_processed_layer, 'weight': weight})
        
        # --- 4. Run Weighted Overlay ---
        if not processed_factors:
            QgsMessageLog.logMessage("No factors could be processed.", "EthioRiskSurv-Toolbox", Qgis.Critical)
            return False

        QgsMessageLog.logMessage("Performing weighted overlay...", "EthioRiskSurv-Toolbox", Qgis.Info)
        
        # Build the raster calculator formula and entries
        formula = ""
        total_weight = 0
        entries = []
        for i, factor in enumerate(processed_factors):
            ref_name = f'factor{i+1}@1'
            formula += f'("{ref_name}" * {factor["weight"]}) + '
            total_weight += factor["weight"]
            
            entry = QgsRasterCalculatorEntry()
            entry.ref = ref_name
            entry.raster = factor['layer']
            entry.bandNumber = 1
            entries.append(entry)
            
        # Complete the formula (normalize by total weight)
        formula = f"({formula.strip(' + ')}) / {total_weight}"

        # --- 5. Clip to Study Area and Finalize ---
        output_risk_map_path = os.path.join(self.project.homePath(), f"{self.project_name.replace(' ', '_')}_RiskMap.tif")
        
        # Setup calculator
        calc = QgsRasterCalculator(
            formula,
            output_risk_map_path,
            'GTiff',
            self.study_area_layer.extent(),
            int(self.study_area_layer.extent().width() / self.resolution),
            int(self.study_area_layer.extent().height() / self.resolution),
            entries
        )
        calc.processCalculation()

        # Clip final raster with study area polygon
        clipped_risk_map_path = os.path.join(self.project.homePath(), f"{self.project_name.replace(' ', '_')}_RiskMap_Clipped.tif")
        params = {
            'INPUT': output_risk_map_path,
            'MASK': self.study_area_layer,
            'OUTPUT': clipped_risk_map_path
        }
        processing.run("gdal:cliprasterbymasklayer", params, context=context, feedback=feedback)

        # Load the final layer into the project
        final_risk_map = QgsRasterLayer(clipped_risk_map_path, f"{self.project_name} - Risk Map")
        if final_risk_map.isValid():
            self.project.addMapLayer(final_risk_map)
            QgsMessageLog.logMessage("Risk analysis completed successfully!", "EthioRiskSurv-Toolbox", Qgis.Success)
            return True
        else:
            QgsMessageLog.logMessage("Failed to create the final clipped risk map.", "EthioRiskSurv-Toolbox", Qgis.Critical)
            return False
