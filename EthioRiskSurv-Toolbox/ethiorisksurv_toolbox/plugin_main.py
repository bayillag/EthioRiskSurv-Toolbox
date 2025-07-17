# -*- coding: utf-8 -*-

import os
import processing
from datetime import datetime
from qgis.PyQt.QtWidgets import (
    QAction, QDialog, QTableWidgetItem, QComboBox, QSpinBox, 
    QFileDialog, QTableWidget, QInputDialog
)
from qgis.PyQt.QtGui import QIcon
from qgis.core import (
    QgsProject, QgsMessageLog, Qgis, QgsMapLayerProxyModel, 
    QgsVectorLayer, QgsRasterLayer, QgsRasterBandStats, QgsPointXY,
    QgsVectorFileWriter
)
from PyQt5.QtCore import Qt
from qgis.utils import iface

# Import UI and all core logic modules
from .ui.main_dialog_ui import Ui_EthioSurvRiskToolboxDialogBase
from .core.risk_analyzer import RiskAnalyzer
from .core.sampling_designer import SamplingDesigner
from .core.cost_evaluator import CostEvaluator
from .core.reporter import Reporter
# ... (other imports)
from .utils.gis_utils import load_resource_layer

class EthioRiskSurvToolbox:
    def __init__(self, iface):
        # ... (existing init code) ...
        self.base_layer_menu = None # Add this line

    def initGui(self):
        """Create the menu entries and toolbar icons."""
        # ... (existing code to add the main action) ...

        # --- Add a new menu for base layers ---
        self.base_layer_menu = self.iface.pluginMenu().addMenu("Load EthioRiskSurv Base Layers")
        
        load_l1_action = QAction("Load Admin Level 1 (Regions)", self.iface.mainWindow())
        load_l1_action.triggered.connect(lambda: load_resource_layer('base_layers/ETH_Admin_Level_1.gpkg', 'Ethiopia - Regions'))
        self.base_layer_menu.addAction(load_l1_action)
        self.actions.append(load_l1_action)

        load_l2_action = QAction("Load Admin Level 2 (Zones)", self.iface.mainWindow())
        load_l2_action.triggered.connect(lambda: load_resource_layer('base_layers/ETH_Admin_Level_2.gpkg', 'Ethiopia - Zones'))
        self.base_layer_menu.addAction(load_l2_action)
        self.actions.append(load_l2_action)

        load_l3_action = QAction("Load Admin Level 3 (Woredas)", self.iface.mainWindow())
        load_l3_action.triggered.connect(lambda: load_resource_layer('base_layers/ETH_Admin_Level_3.gpkg', 'Ethiopia - Woredas'))
        self.base_layer_menu.addAction(load_l3_action)
        self.actions.append(load_l3_action)

    def unload(self):
        """Remove menu items and toolbar icon."""
        # ... (existing code to remove actions and toolbar) ...

        # --- Remove the new menu ---
        if self.base_layer_menu:
            self.iface.pluginMenu().removeAction(self.base_layer_menu.menuAction())
        
        # ... (rest of unload method) ...

    # ... (run method remains the same) ...

class EthioSurvRiskToolboxDialog(QDialog, Ui_EthioSurvRiskToolboxDialogBase):
    """Main dialog for the EthioSurv-RiskToolbox plugin."""
    def __init__(self, parent=None):
        super(EthioSurvRiskToolboxDialog, self).__init__(parent)
        self.setupUi(self)
        
        # --- Initialize state variables to store results between modules ---
        self.classified_risk_raster = None
        self.hq_point = None
        self.last_sampling_plan = None
        self.last_strategy_name = ""
        self.last_risk_map = None
        
        # --- Run setup functions ---
        self.setup_ui_logic()
        self.connect_signals()

    def setup_ui_logic(self):
        """Set up initial state and filters for all UI elements across all tabs."""
        # --- Tab 1 ---
        self.combo_objective.addItems([
            "Early Detection of Incursion", "Demonstrating Freedom from Disease",
            "Prevalence Estimation", "Case Detection / Monitoring"
        ])
        self.mMapLayerComboBox_study_area.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.table_risk_factors.setColumnWidth(0, 200)
        self.table_risk_factors.setColumnWidth(1, 60)
        
        # --- Tab 2 ---
        self.mMapLayerComboBox_risk_map.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.mMapLayerComboBox_snap_layer.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.combo_strategy.addItems(["Simple Random", "Stratified", "Targeted (Risk-Based)"])
        self.table_stratified_n.horizontalHeader().setStretchLastSection(True)
        
        # --- Tab 3 ---
        self.table_scenarios.setColumnWidth(0, 120)
        self.table_scenarios.setColumnWidth(2, 60)
        self.table_scenarios.horizontalHeader().setStretchLastSection(True)

        # --- Tab 4 ---
        self.mMapLayerComboBox_export_layer.setFilters(QgsMapLayerProxyModel.PointLayer)
        # Automatically link the report title to the project name
        self.le_project_name.textChanged.connect(self.le_report_title.setText)

    def connect_signals(self):
        """Connect all UI element signals to their corresponding slots."""
        # Tab 1
        self.btn_add_factor.clicked.connect(self.add_risk_factor_row)
        self.btn_remove_factor.clicked.connect(self.remove_risk_factor_row)
        self.btn_generate_risk_map.clicked.connect(self.run_risk_analysis)
        
        # Tab 2
        self.combo_strategy.currentIndexChanged.connect(self.stackedWidget_params.setCurrentIndex)
        self.btn_classify_risk_map.clicked.connect(self.classify_risk_map)
        self.btn_generate_samples.clicked.connect(self.run_sampling_design)

        # Tab 3
        self.btn_calculate_and_add.clicked.connect(self.run_cost_evaluation)
        self.btn_clear_scenarios.clicked.connect(lambda: self.table_scenarios.setRowCount(0))
        
        # Tab 4
        self.btn_export_layer.clicked.connect(self.export_sampling_layer)
        self.btn_generate_pdf.clicked.connect(self.run_report_generation)

    # ===================================================================
    # METHODS FOR MODULE 1: RISK ANALYSIS
    # ===================================================================
    def add_risk_factor_row(self):
        layers, _ = QFileDialog.getOpenFileNames(self, "Select Risk Factor Layers", "", "Geospatial Files (*.shp *.tif *.gpkg)")
        if not layers: return
        for layer_path in layers:
            layer_name = os.path.basename(layer_path)
            row_position = self.table_risk_factors.rowCount()
            self.table_risk_factors.insertRow(row_position)
            item_name = QTableWidgetItem(layer_name)
            item_name.setData(Qt.UserRole, layer_path)
            self.table_risk_factors.setItem(row_position, 0, item_name)
            spin_box = QSpinBox(); spin_box.setRange(1, 10); self.table_risk_factors.setCellWidget(row_position, 1, spin_box)
            combo_corr = QComboBox(); combo_corr.addItems(["Higher values = Higher Risk", "Lower values = Higher Risk"]); self.table_risk_factors.setCellWidget(row_position, 2, combo_corr)
            layer_type = "Vector" if layer_path.lower().endswith(('.shp', '.gpkg')) else "Raster"
            self.table_risk_factors.setItem(row_position, 3, QTableWidgetItem(layer_type))
            
    def remove_risk_factor_row(self):
        current_row = self.table_risk_factors.currentRow()
        if current_row > -1: self.table_risk_factors.removeRow(current_row)

    def run_risk_analysis(self):
        project_name = self.le_project_name.text()
        study_area_layer = self.mMapLayerComboBox_study_area.currentLayer()
        resolution = self.spinBox_resolution.value()
        if not project_name or not study_area_layer:
            iface.messageBar().pushMessage("Error", "Project Name and Study Area Layer are required.", level=Qgis.Critical)
            return
        risk_factors_data = []
        for row in range(self.table_risk_factors.rowCount()):
            layer_path = self.table_risk_factors.item(row, 0).data(Qt.UserRole)
            layer_type = self.table_risk_factors.item(row, 3).text()
            layer = QgsVectorLayer(layer_path, "tmp", "ogr") if layer_type == "Vector" else QgsRasterLayer(layer_path, "tmp")
            if not layer.isValid():
                iface.messageBar().pushMessage("Error", f"Could not load layer: {layer_path}", level=Qgis.Critical); return
            risk_factors_data.append({'layer': layer, 'weight': self.table_risk_factors.cellWidget(row, 1).value(), 'correlation': self.table_risk_factors.cellWidget(row, 2).currentText()})
        if not risk_factors_data:
            iface.messageBar().pushMessage("Error", "Please add at least one risk factor.", level=Qgis.Critical); return
        try:
            iface.messageBar().pushMessage("Info", "Starting risk analysis...", level=Qgis.Info, duration=10)
            analyzer = RiskAnalyzer(study_area_layer, risk_factors_data, resolution, project_name)
            success, final_map = analyzer.run()
            if success and final_map:
                self.last_risk_map = final_map
                self.mMapLayerComboBox_risk_map.setLayer(self.last_risk_map) # Auto-populate in Tab 2
                iface.messageBar().pushMessage("Success", f"Risk Map for '{project_name}' created!", level=Qgis.Success, duration=10)
                self.tab_widget.setCurrentIndex(1)
            else:
                iface.messageBar().pushMessage("Error", "Risk analysis failed. Check QGIS Message Log.", level=Qgis.Critical)
        except Exception as e:
            QgsMessageLog.logMessage(f"An error occurred: {str(e)}", "EthioSurv-RiskToolbox", Qgis.Critical)

    # ===================================================================
    # METHODS FOR MODULE 2: SAMPLING DESIGN
    # ===================================================================
    def classify_risk_map(self):
        risk_map = self.mMapLayerComboBox_risk_map.currentLayer()
        if not risk_map: iface.messageBar().pushMessage("Error", "Please select a Risk Map Layer.", level=Qgis.Critical); return
        num_strata = self.spinBox_strata_count.value()
        stats = risk_map.dataProvider().bandStatistics(1, QgsRasterBandStats.All)
        min_val, max_val = stats.minimumValue, stats.maximumValue
        step = (max_val - min_val) / num_strata
        reclass_table = [[min_val + (i * step), min_val + ((i + 1) * step), i + 1] for i in range(num_strata)]
        reclass_table[-1][1] = max_val
        params = {'INPUT_RASTER': risk_map, 'RASTER_BAND': 1, 'TABLE': reclass_table, 'OUTPUT': 'memory:'}
        result = processing.run("native:reclassifybytable", params)
        self.classified_risk_raster = result['OUTPUT']
        self.classified_risk_raster.setName(f"{risk_map.name()}_{num_strata}_Strata")
        QgsProject.instance().addMapLayer(self.classified_risk_raster)
        self.table_stratified_n.setRowCount(num_strata)
        for i in range(num_strata):
            self.table_stratified_n.setItem(i, 0, QTableWidgetItem(f"Stratum {i+1}"))
            spin_box = QSpinBox(); spin_box.setMaximum(99999); self.table_stratified_n.setCellWidget(i, 1, spin_box)
        iface.messageBar().pushMessage("Success", "Risk map classified and table populated.", level=Qgis.Success)

    def run_sampling_design(self):
        strategy_name = self.combo_strategy.currentText()
        risk_map = self.mMapLayerComboBox_risk_map.currentLayer()
        study_area = self.mMapLayerComboBox_study_area.currentLayer()
        snap_layer = self.mMapLayerComboBox_snap_layer.currentLayer()
        output_name = self.le_output_name.text()
        if not risk_map or not study_area: iface.messageBar().pushMessage("Error", "Risk Map and Study Area layers are required.", level=Qgis.Critical); return
        designer = SamplingDesigner(risk_map, study_area, output_name, snap_layer)
        result_layer = None
        try:
            if strategy_name == "Simple Random": result_layer = designer.generate_random_points(self.spinBox_random_n.value())
            elif strategy_name == "Targeted (Risk-Based)": result_layer = designer.generate_targeted_points(self.doubleSpinBox_risk_threshold.value(), self.spinBox_targeted_n.value())
            elif strategy_name == "Stratified":
                if not self.classified_risk_raster: iface.messageBar().pushMessage("Error", "Please classify the risk map first.", level=Qgis.Critical); return
                strata_counts = {i + 1: self.table_stratified_n.cellWidget(i, 1).value() for i in range(self.table_stratified_n.rowCount())}
                result_layer = designer.generate_stratified_points(self.classified_risk_raster, strata_counts)
            if result_layer and result_layer.isValid():
                iface.messageBar().pushMessage("Success", f"Sampling points generated: {result_layer.name()}", level=Qgis.Success)
                self.last_sampling_plan = result_layer
                self.last_strategy_name = strategy_name
                self.mMapLayerComboBox_export_layer.setLayer(self.last_sampling_plan) # Auto-populate in Tab 4
                self.tab_widget.setCurrentIndex(2)
            else: iface.messageBar().pushMessage("Warning", "Sampling point generation did not produce a valid output.", level=Qgis.Warning)
        except Exception as e: QgsMessageLog.logMessage(f"An error occurred during sampling design: {str(e)}", "EthioSurv-RiskToolbox", Qgis.Critical)

    # ===================================================================
    # METHODS FOR MODULE 3: COST EVALUATION
    # ===================================================================
    def run_cost_evaluation(self):
        if not self.last_sampling_plan or not self.last_sampling_plan.isValid(): iface.messageBar().pushMessage("Error", "Please generate a sampling plan in Tab 2 first.", level=Qgis.Critical); return
        study_area_layer = self.mMapLayerComboBox_study_area.currentLayer()
        if not study_area_layer: iface.messageBar().pushMessage("Error", "Study Area layer is required.", level=Qgis.Critical); return
        self.hq_point = study_area_layer.extent().center()
        cost_params = {'cost_per_sample': self.spinBox_cost_per_sample.value(), 'cost_per_diem': self.spinBox_cost_per_diem.value(), 'team_size': self.spinBox_team_size.value(), 'samples_per_day': self.spinBox_samples_per_day.value(), 'cost_per_km': self.spinBox_cost_per_km.value(), 'hq_point': self.hq_point}
        evaluator = CostEvaluator(self.last_sampling_plan, cost_params)
        results = evaluator.calculate_total_cost()
        if not results: iface.messageBar().pushMessage("Error", "Cost evaluation failed.", level=Qgis.Critical); return
        scenario_name, ok = QInputDialog.getText(self, "Scenario Name", "Enter a name for this scenario:", text=self.last_sampling_plan.name())
        if not ok or not scenario_name: scenario_name = self.last_sampling_plan.name()
        row_position = self.table_scenarios.rowCount()
        self.table_scenarios.insertRow(row_position)
        self.table_scenarios.setItem(row_position, 0, QTableWidgetItem(scenario_name))
        self.table_scenarios.setItem(row_position, 1, QTableWidgetItem(self.last_strategy_name))
        self.table_scenarios.setItem(row_position, 2, QTableWidgetItem(str(results['num_samples'])))
        self.table_scenarios.setItem(row_position, 3, QTableWidgetItem(f"{results['total_cost']:.0f}"))
        self.table_scenarios.setItem(row_position, 4, QTableWidgetItem(f"{results['cost_per_sample']:.0f}"))

    # ===================================================================
    # METHODS FOR MODULE 4: REPORT & EXPORT
    # ===================================================================
    def export_sampling_layer(self):
        layer_to_export = self.mMapLayerComboBox_export_layer.currentLayer()
        if not layer_to_export: iface.messageBar().pushMessage("Error", "Please select a layer to export.", level=Qgis.Critical); return
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Layer", "", "ESRI Shapefile (*.shp);;GeoPackage (*.gpkg);;GPS eXchange Format (*.gpx);;Keyhole Markup Language (*.kml);;Comma Separated Value (*.csv)")
        if not file_path: return
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = os.path.splitext(file_path)[1].lower().replace('.', '') if os.path.splitext(file_path)[1].lower() != '.shp' else 'ESRI Shapefile'
        status, err = QgsVectorFileWriter.writeAsVectorFormatV3(layer_to_export, file_path, QgsProject.instance().transformContext(), options)
        if status == QgsVectorFileWriter.NoError: iface.messageBar().pushMessage("Success", f"Layer exported to {file_path}", level=Qgis.Success)
        else: iface.messageBar().pushMessage("Error", f"Export failed: {err}", level=Qgis.Critical)

    def run_report_generation(self):
        map_image_path = os.path.join(QgsProject.instance().homePath(), "temp_report_map.png")
        iface.mapCanvas().saveAsImage(map_image_path)
        report_data = {
            'report_title': self.le_report_title.text(), 'report_author': self.le_report_author.text(),
            'report_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'project_name': self.le_project_name.text(),
            'objective': self.combo_objective.currentText(), 'study_area_name': self.mMapLayerComboBox_study_area.currentLayer().name() if self.mMapLayerComboBox_study_area.currentLayer() else "N/A",
            'sampling_strategy': self.last_strategy_name, 'total_samples': self.last_sampling_plan.featureCount() if self.last_sampling_plan else "N/A",
            'snap_layer_name': self.mMapLayerComboBox_snap_layer.currentLayer().name() if self.mMapLayerComboBox_snap_layer.currentLayer() else None,
            'map_image_path': map_image_path, 'risk_factors': [], 'cost_scenarios': []
        }
        for row in range(self.table_risk_factors.rowCount()): report_data['risk_factors'].append({'name': self.table_risk_factors.item(row, 0).text(), 'weight': self.table_risk_factors.cellWidget(row, 1).value(), 'correlation': self.table_risk_factors.cellWidget(row, 2).currentText()})
        for row in range(self.table_scenarios.rowCount()): report_data['cost_scenarios'].append([self.table_scenarios.item(row, col).text() for col in range(self.table_scenarios.columnCount())])
        if self.table_scenarios.rowCount() > 0: report_data['total_cost'] = float(self.table_scenarios.item(self.table_scenarios.rowCount() - 1, 3).text().replace(',', ''))
        save_path, _ = QFileDialog.getSaveFileName(self, "Save PDF Report", "", "PDF Documents (*.pdf)")
        if not save_path: os.remove(map_image_path); return
        reporter = Reporter(report_data)
        success = reporter.build_report(save_path)
        os.remove(map_image_path)
        if success: iface.messageBar().pushMessage("Success", f"PDF report saved to {save_path}", level=Qgis.Success)
        else: iface.messageBar().pushMessage("Error", "Failed to generate PDF report.", levelQgis.Critical)

class EthioSurvRiskToolbox:
    """QGIS Plugin Implementation."""
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = "&EthioSurv-RiskToolbox"
        self.toolbar = self.iface.addToolBar("EthioSurvRiskToolboxBar")
        self.toolbar.setObjectName("EthioSurvRiskToolboxBar")
        self.dlg = None

    def add_action(self, icon_path, text, callback, parent=None):
        action = QAction(QIcon(icon_path), text, parent)
        action.triggered.connect(callback)
        self.iface.addToolBarIcon(action)
        self.iface.addPluginToMenu(self.menu, action)
        self.actions.append(action)
        return action

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, "icon.png")
        self.add_action(icon_path, "Launch EthioSurv-RiskToolbox", self.run, self.iface.mainWindow())

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

    def run(self):
        if self.dlg is None:
            self.dlg = EthioSurvRiskToolboxDialog(self.iface.mainWindow())
        self.dlg.show()
