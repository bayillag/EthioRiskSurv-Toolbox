# -*- coding: utf-8 -*-

import math
from qgis.core import QgsMessageLog, Qgis, QgsDistanceArea

class CostEvaluator:
    """
    Handles all core logic for Module 3: Cost-Effectiveness Evaluation.
    """
    def __init__(self, sampling_layer, cost_params):
        """
        Constructor.
        :param sampling_layer: QgsVectorLayer of sampling points.
        :param cost_params: A dictionary containing all cost parameters from the UI.
        """
        self.sampling_layer = sampling_layer
        self.params = cost_params

    def calculate_total_cost(self):
        """
        Calculates the total estimated cost for the given surveillance plan.
        Returns a dictionary with detailed cost breakdowns.
        """
        QgsMessageLog.logMessage("Starting cost evaluation.", "EthioSurv-RiskToolbox", Qgis.Info)

        if not self.sampling_layer or self.sampling_layer.featureCount() == 0:
            QgsMessageLog.logMessage("No sampling points to evaluate.", "EthioSurv-RiskToolbox", Qgis.Warning)
            return None

        # --- 1. Get counts and basic parameters ---
        num_samples = self.sampling_layer.featureCount()
        samples_per_day = self.params.get('samples_per_day', 1)
        team_size = self.params.get('team_size', 1)

        # --- 2. Calculate Fixed Per-Sample Costs ---
        cost_per_sample = self.params.get('cost_per_sample', 0)
        fixed_costs = num_samples * cost_per_sample
        
        # --- 3. Calculate Personnel & Time Costs ---
        # Ceiling function ensures we account for partial days
        total_field_days = math.ceil(num_samples / samples_per_day)
        cost_per_diem = self.params.get('cost_per_diem', 0)
        personnel_costs = total_field_days * team_size * cost_per_diem

        # --- 4. Calculate Logistics (Travel) Costs ---
        # For this version, we use simple straight-line distance.
        # An advanced version would use a road network and a routing algorithm.
        logistics_costs = 0
        hq_point = self.params.get('hq_point')
        cost_per_km = self.params.get('cost_per_km', 0)

        if hq_point and hq_point.isGeosValid():
            d = QgsDistanceArea()
            d.setEllipsoid(QgsProject.instance().ellipsoid())
            total_distance_m = 0
            for point_feature in self.sampling_layer.getFeatures():
                point_geom = point_feature.geometry()
                # Distance from HQ to point and back
                distance = d.measureLine(hq_point, point_geom.asPoint()) * 2
                total_distance_m += distance
            
            total_distance_km = total_distance_m / 1000
            logistics_costs = total_distance_km * cost_per_km
            QgsMessageLog.logMessage(f"Total travel distance calculated: {total_distance_km:.2f} km", "EthioSurv-RiskToolbox", Qgis.Info)
        else:
            QgsMessageLog.logMessage("HQ point not set. Logistics costs will be zero.", "EthioSurv-RiskToolbox", Qgis.Warning)

        # --- 5. Aggregate and return results ---
        total_cost = fixed_costs + personnel_costs + logistics_costs
        cost_per_sample_final = total_cost / num_samples if num_samples > 0 else 0
        
        results = {
            'num_samples': num_samples,
            'total_cost': total_cost,
            'cost_per_sample': cost_per_sample_final,
            'breakdown': {
                'fixed_costs': fixed_costs,
                'personnel_costs': personnel_costs,
                'logistics_costs': logistics_costs
            }
        }
        
        QgsMessageLog.logMessage(f"Cost evaluation complete. Total estimated cost: {total_cost:.2f} ETB", "EthioSurv-RiskToolbox", Qgis.Success)
        return results