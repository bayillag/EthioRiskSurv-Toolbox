# -*- coding: utf-8 -*-

def classFactory(iface):
    """Load EthioSurvRiskToolbox class from file plugin_main.py."""
    from .plugin_main import EthioSurvRiskToolbox
    return EthioSurvRiskToolbox(iface)