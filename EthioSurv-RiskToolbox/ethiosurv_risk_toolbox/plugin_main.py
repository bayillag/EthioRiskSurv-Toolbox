# -*- coding: utf-8 -*-

import os
from qgis.PyQt.QtWidgets import QAction, QDialog
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProject, QgsMessageLog, Qgis, QgsMapLayerProxyModel
from qgis.utils import iface

# This step is crucial. Before running the plugin, you need to compile the .ui file.
# In your terminal, run: pyuic5 -x ethiosurv_risk_toolbox/ui/main_dialog.ui -o ethiosurv_risk_toolbox/ui/main_dialog_ui.py
# If that command fails, it means you need to install pyqt5-dev-tools:
# python3 -m pip install pyqt5-dev-tools
from .ui.main_dialog_ui import Ui_EthioSurvRiskToolboxDialogBase

# Import logic from the core modules (even if they are empty for now)
from .core.risk_analyzer import RiskAnalyzer

class EthioSurvRiskToolboxDialog(QDialog, Ui_EthioSurvRiskToolboxDialogBase):
    """Main dialog for the EthioSurv-RiskToolbox plugin."""
    def __init__(self, parent=None):
        super(EthioSurvRiskToolboxDialog, self).__init__(parent)
        self.setupUi(self)
        self.setup_ui_logic()
        self.connect_signals()

    def setup_ui_logic(self):
        """Set up initial state and filters for UI elements."""
        # Populate the objectives combo box
        self.combo_objective.addItems([
            "Early Detection of Incursion",
            "Demonstrating Freedom from Disease",
            "Prevalence Estimation",
            "Case Detection / Monitoring"
        ])
        
        # Filter the map layer combo box to only show polygon layers
        self.mMapLayerComboBox_study_area.setFilters(QgsMapLayerProxyModel.PolygonLayer)

    def connect_signals(self):
        """Connect UI element signals to corresponding slots (functions)."""
        self.btn_add_factor.clicked.connect(self.add_risk_factor_row)
        self.btn_generate_risk_map.clicked.connect(self.run_risk_analysis)

    def add_risk_factor_row(self):
        """A placeholder to add a new row to the risk factor table."""
        # This is where you would open a dialog to select a layer
        row_position = self.table_risk_factors.rowCount()
        self.table_risk_factors.insertRow(row_position)
        iface.messageBar().pushMessage(
            "Info", "New row added. In a future version, you will select a layer here.",
            level=Qgis.Info, duration=3)
            
    def run_risk_analysis(self):
        """
        Gathers data from the UI and calls the core RiskAnalyzer class to perform the analysis.
        """
        # --- 1. Gather Inputs from UI ---
        project_name = self.le_project_name.text()
        objective = self.combo_objective.currentText()
        study_area_layer = self.mMapLayerComboBox_study_area.currentLayer()
        
        # --- 2. Validate Inputs ---
        if not project_name or not study_area_layer:
            iface.messageBar().pushMessage(
                "Error", "Project Name and Study Area Layer are required.",
                level=Qgis.Critical, duration=5)
            return

        # --- 3. Pass to Core Logic ---
        # This is where the separation of concerns happens. The UI class doesn't do the GIS work.
        # It calls another class dedicated to that task.
        log_message = f"Starting Risk Analysis for project: '{project_name}'"
        QgsMessageLog.logMessage(log_message, "EthioSurv-RiskToolbox", Qgis.Info)

        try:
            # For now, RiskAnalyzer's run method will just be a placeholder
            analyzer = RiskAnalyzer(study_area_layer, {}) # Pass empty risk factors for now
            result = analyzer.run() # In the future, this will return a raster layer
            
            if result:
                iface.messageBar().pushMessage(
                    "Success", f"Risk analysis simulation for '{project_name}' completed successfully!",
                    level=Qgis.Success, duration=5)
                self.close() # Close the dialog on success
            else:
                iface.messageBar().pushMessage(
                    "Error", "Risk analysis simulation failed. Check the QGIS Message Log.",
                    level=Qgis.Critical, duration=5)

        except Exception as e:
            QgsMessageLog.logMessage(f"An error occurred: {str(e)}", "EthioSurv-RiskToolbox", Qgis.Critical)
            iface.messageBar().pushMessage("Error", f"An unexpected error occurred: {str(e)}", level=Qgis.Critical)


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
        """Helper to add a QAction to the menu and toolbar."""
        action = QAction(QIcon(icon_path), text, parent)
        action.triggered.connect(callback)
        self.iface.addToolBarIcon(action)
        self.iface.addPluginToMenu(self.menu, action)
        self.actions.append(action)
        return action

    def initGui(self):
        """Create the menu entries and toolbar icons."""
        icon_path = os.path.join(self.plugin_dir, "icon.png")
        self.add_action(
            icon_path,
            text="Launch EthioSurv-RiskToolbox",
            callback=self.run,
            parent=self.iface.mainWindow()
        )

    def unload(self):
        """Remove menu item and toolbar icon."""
        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

    def run(self):
        """Run method that performs all the work."""
        # Create the dialog only if it doesn't exist
        if self.dlg is None:
            self.dlg = EthioSurvRiskToolboxDialog(self.iface.mainWindow())
        
        # Show the dialog
        self.dlg.show()