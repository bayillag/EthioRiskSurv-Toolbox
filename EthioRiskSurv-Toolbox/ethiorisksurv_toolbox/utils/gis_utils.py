# -*- coding: utf-8 -*-

from qgis.core import QgsProcessing, QgsProcessingAlgorithm, QgsProcessingParameterRasterLayer, QgsProcessingParameterNumber, QgsProcessingParameterRasterDestination
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry

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