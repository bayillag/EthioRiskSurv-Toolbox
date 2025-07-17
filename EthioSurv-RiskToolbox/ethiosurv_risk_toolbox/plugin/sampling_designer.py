# -*- coding: utf-8 -*-

import os
import processing
from qgis.core import (
    QgsMessageLog, Qgis, QgsVectorLayer, QgsRasterLayer, QgsProject,
    QgsProcessingContext, QgsProcessingFeedback, QgsFeature, QgsGeometry,
    QgsField, QgsFeatureSink, QgsFields, QgsWkbTypes
)
from PyQt5.QtCore import QVariant

class SamplingDesigner:
    """
    Handles all core logic for Module 2: Sampling Strategy Design.
    """
    def __init__(self, risk_map_layer, study_area_layer, output_name, snap_layer=None):
        self.risk_map = risk_map_layer
        self.study_area = study_area_layer
        self.output_name = output_name if output_name else "Sampling_Points"
        self.snap_layer = snap_layer
        self.project = QgsProject.instance()
        self.context = QgsProcessingContext()
        self.feedback = QgsProcessingFeedback()

    def generate_random_points(self, count):
        """Generates simple random points within the study area."""
        QgsMessageLog.logMessage(f"Generating {count} random points.", "EthioSurv-RiskToolbox", Qgis.Info)
        
        params = {
            'INPUT': self.study_area,
            'POINTS_NUMBER': count,
            'OUTPUT': 'memory:'
        }
        result = processing.run("qgis:randompointsinsidepolygons", params, context=self.context, feedback=self.feedback)
        return self._finalize_output(result['OUTPUT'])

    def generate_stratified_points(self, classified_raster, strata_counts):
        """Generates points within each stratum of a classified raster."""
        QgsMessageLog.logMessage(f"Generating stratified points for {len(strata_counts)} strata.", "EthioSurv-RiskToolbox", Qgis.Info)

        final_points = []
        for stratum_value, count in strata_counts.items():
            if count == 0:
                continue
            
            # Create a mask for the current stratum
            expr = f'"{classified_raster.name()}@1" = {stratum_value}'
            stratum_mask_path = 'memory:'
            params = {
                'EXPRESSION': expr,
                'LAYERS': [classified_raster],
                'OUTPUT': stratum_mask_path
            }
            mask_result = processing.run("qgis:rastercalculator", params, context=self.context, feedback=self.feedback)
            mask_raster = mask_result['OUTPUT']
            
            # Polygonize the mask
            polygon_path = 'memory:'
            params = {
                'INPUT': mask_raster,
                'BAND': 1,
                'OUTPUT': polygon_path
            }
            polygon_result = processing.run("gdal:polygonize", params, context=self.context, feedback=self.feedback)
            stratum_polygon = polygon_result['OUTPUT']
            
            # Generate random points within the stratum polygon
            params = {
                'INPUT': stratum_polygon,
                'POINTS_NUMBER': count,
                'OUTPUT': 'memory:'
            }
            points_result = processing.run("qgis:randompointsinsidepolygons", params, context=self.context, feedback=self.feedback)
            
            for feature in points_result['OUTPUT'].getFeatures():
                final_points.append(feature)

        return self._create_layer_from_features(final_points)

    def generate_targeted_points(self, threshold, count):
        """Generates random points within areas exceeding a risk threshold."""
        QgsMessageLog.logMessage(f"Generating {count} targeted points with threshold > {threshold}.", "EthioSurv-RiskToolbox", Qgis.Info)
        
        # Create a mask of high-risk areas
        expr = f'"{self.risk_map.name()}@1" >= {threshold}'
        params = {
            'EXPRESSION': expr, 'LAYERS': [self.risk_map], 'OUTPUT': 'memory:'
        }
        mask_result = processing.run("qgis:rastercalculator", params, context=self.context, feedback=self.feedback)
        
        # Polygonize the mask
        params = {
            'INPUT': mask_result['OUTPUT'], 'BAND': 1, 'OUTPUT': 'memory:'
        }
        polygon_result = processing.run("gdal:polygonize", params, context=self.context, feedback=self.feedback)
        high_risk_polygons = polygon_result['OUTPUT']
        
        # Generate points inside the high-risk polygons
        params = {
            'INPUT': high_risk_polygons, 'POINTS_NUMBER': count, 'OUTPUT': 'memory:'
        }
        points_result = processing.run("qgis:randompointsinsidepolygons", params, context=self.context, feedback=self.feedback)
        return self._finalize_output(points_result['OUTPUT'])

    def _create_layer_from_features(self, features):
        """Helper to create a new point layer from a list of features."""
        fields = QgsFields()
        fields.append(QgsField("ID", QVariant.Int))
        
        # Create a memory layer
        sink, dest_id = QgsVectorLayer("Point?crs=" + self.study_area.crs().authid(), "temporary_points", "memory").dataProvider().addFeatures([], QgsFeatureSink.FastInsert)
        
        new_feats = []
        for i, feat in enumerate(features):
            new_feat = QgsFeature(fields)
            new_feat.setGeometry(feat.geometry())
            new_feat.setAttribute("ID", i + 1)
            new_feats.append(new_feat)
        
        sink.addFeatures(new_feats)
        layer = self.project.layerStore().sourceLayer(dest_id)
        return self._finalize_output(layer)

    def _finalize_output(self, points_layer):
        """Helper to handle snapping and adding the final layer to the project."""
        if not points_layer or points_layer.featureCount() == 0:
            QgsMessageLog.logMessage("No points were generated.", "EthioSurv-RiskToolbox", Qgis.Warning)
            return None

        final_layer = points_layer
        # Snapping logic
        if self.snap_layer and self.snap_layer.isValid():
            QgsMessageLog.logMessage(f"Snapping points to layer: {self.snap_layer.name()}", "EthioSurv-RiskToolbox", Qgis.Info)
            params = {
                'INPUT': points_layer,
                'REFERENCE_LAYER': self.snap_layer,
                'BEHAVIOR': 0, # Prefer closest point
                'OUTPUT': 'memory:'
            }
            result = processing.run("qgis:snappointstogrid", params, context=self.context, feedback=self.feedback)
            final_layer = result['OUTPUT']
        
        final_layer.setName(self.output_name)
        self.project.addMapLayer(final_layer)
        return final_layer