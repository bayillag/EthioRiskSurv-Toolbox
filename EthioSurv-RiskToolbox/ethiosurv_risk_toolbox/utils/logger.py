# -*- coding: utf-8 -*-

from qgis.core import QgsMessageLog, Qgis

# Define the plugin's name, which will be used as the log message tag.
# This ensures all messages from this plugin are grouped together in the log panel.
PLUGIN_NAME = "EthioSurv-RiskToolbox"

class Logger:
    """
    A simple logging utility class to standardize messages sent to the
    QGIS Message Log panel.
    """

    @staticmethod
    def log_info(message):
        """
        Logs an informational message. Use for general status updates,
        like "Starting process X..."

        :param message: The string message to log.
        """
        QgsMessageLog.logMessage(str(message), PLUGIN_NAME, Qgis.Info)

    @staticmethod
    def log_success(message):
        """
        Logs a success message. Use when a process completes successfully.

        :param message: The string message to log.
        """
        QgsMessageLog.logMessage(str(message), PLUGIN_NAME, Qgis.Success)

    @staticmethod
    def log_warning(message):
        """
        Logs a warning message. Use for non-critical issues that the user
        should be aware of, e.g., "Input layer has no features."

        :param message: The string message to log.
        """
        QgsMessageLog.logMessage(str(message), PLUGIN_NAME, Qgis.Warning)

    @staticmethod
    def log_error(message):
        """
        Logs a critical error message. Use when a process fails or an
        unexpected exception occurs.

        :param message: The string message to log.
        """
        QgsMessageLog.logMessage(str(message), PLUGIN_NAME, Qgis.Critical)

# You can also create top-level functions for even easier access if you prefer.
# This allows for calling `log.info(...)` instead of `Logger.log_info(...)`.
info = Logger.log_info
success = Logger.log_success
warning = Logger.log_warning
error = Logger.log_error