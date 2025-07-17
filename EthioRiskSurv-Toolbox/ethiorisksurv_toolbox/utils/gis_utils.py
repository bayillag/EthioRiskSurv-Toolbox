# -*- coding: utf-8 -*-

from qgis.core import QgsProcessing, QgsProcessingAlgorithm, QgsProcessingParameterRasterLayer, QgsProcessingParameterNumber, QgsProcessingParameterRasterDestination
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
from qgis.core import QgsVectorLayer, QgsProject, QgsMessageLog, Qgis
from ..utils import logger

# --- NEW: Define our known resource layers ---
# This dictionary maps a user-friendly name to its resource alias.
RESOURCE_LAYERS = {
    "Ethiopia - Regions (Admin 1)": "base_layers/ETH_Admin_Level_1.gpkg",
    "Ethiopia - Zones (Admin 2)": "base_layers/ETH_Admin_Level_2.gpkg",
    "Ethiopia - Woredas (Admin 3)": "base_layers/ETH_Admin_Level_3.gpkg"
}

# --- NEW: Function to get a layer (either from project or resource) ---
def get_layer_by_name(layer_name):
    """
    Gets a layer object. First, it checks if a layer with that name
    is already in the QGIS project. If not, it tries to load it from
    the plugin's resources.

    :param layer_name: The user-friendly name of the layer.
    :return: QgsVectorLayer or None.
    """
    # Check if the layer is already loaded in the project
    project = QgsProject.instance()
    layers = project.mapLayersByName(layer_name)
    if layers:
        logger.info(f"Found existing layer in project: '{layer_name}'")
        return layers[0]

    # If not in project, check if it's a known resource layer
    if layer_name in RESOURCE_LAYERS:
        logger.info(f"Loading base layer from resources: '{layer_name}'")
        layer_alias = RESOURCE_LAYERS[layer_name]
        
        # The path to a resource is prefixed with :/
        resource_path = f":/plugins/ethiorisksurv_toolbox/resources/{layer_alias}"
        vsi_path = f"/vsiqrc{resource_path}"
        
        layer = QgsVectorLayer(vsi_path, layer_name, "ogr")
        
        if not layer.isValid():
            logger.error(f"Failed to load resource layer: {layer_name}")
            return None
            
        # Add the newly loaded layer to the project for the user to see
        project.addMapLayer(layer)
        return layer

    # If the layer is not in the project and not a known resource, return None
    logger.warning(f"Layer '{layer_name}' not found in project or base layers.")
    return None

# ... (The existing normalize_raster function can remain here) ...
def normalize_raster(input_layer, output_path):
    """
    Normalizes a raster layer to a 0-1 scale.
    :param input_layer: QgsRasterLayer to normalize.
    :param output_path: Path for the normalized output raster.
    :return: QgsRasterLayer object of the normalized raster, or None on failure.
    """
    # Get raster statistics
    stats = input_layer.dataProvider().bandStatistics(1, QgsRasterBandStats.All)
    min_val = stats.minimumValue
    max_val = stats.maximumValue

    if min_val is None or max_val is None or min_val == max_val:
        # Cannot normalize if there's no data or all values are the same
        return None

    # Setup raster calculator entry
    entry = QgsRasterCalculatorEntry()
    entry.ref = 'input@1'
    entry.raster = input_layer
    entry.bandNumber = 1
    entries = [entry]

    # Formula: (layer - min) / (max - min)
    formula = f"(\"{entry.ref}\" - {min_val}) / ({max_val} - {min_val})"
    
    # Setup calculator
    calc = QgsRasterCalculator(
        formula,
        output_path,
        'GTiff',
        input_layer.extent(),
        input_layer.width(),
        input_layer.height(),
        entries
    )

    # Run calculation
    if calc.processCalculation() != QgsRasterCalculator.NoError:
        return None
    
    # Return the new layer object
    return QgsRasterLayer(output_path, 'normalized_raster')
