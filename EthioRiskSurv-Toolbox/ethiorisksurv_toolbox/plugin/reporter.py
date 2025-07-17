# -*- coding: utf-8 -*-

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors
from reportlab.lib.units import inch
from qgis.core import QgsMessageLog, Qgis

class Reporter:
    """
    Handles all core logic for Module 4: PDF Reporting.
    """
    def __init__(self, report_data):
        self.data = report_data
        self.styles = getSampleStyleSheet()
        self.story = []

    def build_report(self, output_path):
        """Builds and saves the PDF report."""
        try:
            doc = SimpleDocTemplate(output_path,
                                    rightMargin=0.75*inch, leftMargin=0.75*inch,
                                    topMargin=1.0*inch, bottomMargin=1.0*inch)
            
            self._create_title_page()
            self._create_risk_analysis_section()
            self._create_sampling_design_section()
            self._create_cost_evaluation_section()
            
            doc.build(self.story)
            QgsMessageLog.logMessage("PDF report built successfully.", "EthioSurv-RiskToolbox", Qgis.Success)
            return True
        except Exception as e:
            QgsMessageLog.logMessage(f"Failed to build PDF report: {e}", "EthioSurv-RiskToolbox", Qgis.Critical)
            return False

    def _create_title_page(self):
        """Creates the first page of the report."""
        self.story.append(Paragraph(self.data.get('report_title', 'Surveillance Plan'), self.styles['h1']))
        self.story.append(Spacer(1, 0.2*inch))
        self.story.append(Paragraph(f"Author: {self.data.get('report_author', 'N/A')}", self.styles['Normal']))
        self.story.append(Paragraph(f"Date Generated: {self.data.get('report_date', 'N/A')}", self.styles['Normal']))
        self.story.append(Spacer(1, 0.5*inch))
        
        # Executive Summary Table
        summary_data = [
            ['Parameter', 'Value'],
            ['Project Name', self.data.get('project_name', 'N/A')],
            ['Surveillance Objective', self.data.get('objective', 'N/A')],
            ['Study Area', self.data.get('study_area_name', 'N/A')],
            ['Sampling Strategy', self.data.get('sampling_strategy', 'N/A')],
            ['Total Samples', str(self.data.get('total_samples', 'N/A'))],
            ['Estimated Total Cost (ETB)', f"{self.data.get('total_cost', 0):,.0f}"]
        ]
        
        table = Table(summary_data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.beige),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        self.story.append(table)
        self.story.append(PageBreak())

    def _create_risk_analysis_section(self):
        """Adds the risk analysis details to the report."""
        self.story.append(Paragraph("Module 1: Risk Analysis Details", self.styles['h2']))
        self.story.append(Spacer(1, 0.2*inch))
        self.story.append(Paragraph("The final risk map was generated using a weighted overlay of the following factors:", self.styles['Normal']))
        self.story.append(Spacer(1, 0.1*inch))
        
        risk_factors = self.data.get('risk_factors', [])
        if risk_factors:
            table_data = [['Risk Factor Layer', 'Weight', 'Correlation']]
            for factor in risk_factors:
                table_data.append([factor['name'], str(factor['weight']), factor['correlation']])
            
            table = Table(table_data, colWidths=[3*inch, 1*inch, 2*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
                ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
                ('GRID', (0,0), (-1,-1), 1, colors.black)
            ]))
            self.story.append(table)
        
        # Add map image
        map_image_path = self.data.get('map_image_path')
        if map_image_path:
            self.story.append(Spacer(1, 0.3*inch))
            self.story.append(Paragraph("Final Risk Map and Sampling Points:", self.styles['h3']))
            img = Image(map_image_path, width=6*inch, height=4.5*inch)
            img.hAlign = 'CENTER'
            self.story.append(img)
        self.story.append(PageBreak())

    def _create_sampling_design_section(self):
        """Adds the sampling design details."""
        self.story.append(Paragraph("Module 2: Sampling Design Details", self.styles['h2']))
        self.story.append(Spacer(1, 0.2*inch))
        self.story.append(Paragraph(f"A <b>{self.data.get('sampling_strategy', 'N/A')}</b> strategy was employed.", self.styles['Normal']))
        self.story.append(Paragraph(f"A total of <b>{self.data.get('total_samples', 'N/A')}</b> points were generated.", self.styles['Normal']))
        if self.data.get('snap_layer_name'):
             self.story.append(Paragraph(f"Points were snapped to the nearest feature in: {self.data.get('snap_layer_name')}", self.styles['Normal']))

    def _create_cost_evaluation_section(self):
        """Adds the cost evaluation details."""
        self.story.append(Spacer(1, 0.5*inch))
        self.story.append(Paragraph("Module 3: Cost Evaluation Summary", self.styles['h2']))
        self.story.append(Spacer(1, 0.2*inch))
        
        cost_scenarios = self.data.get('cost_scenarios', [])
        if cost_scenarios:
            table_data = [['Scenario', 'Strategy', '# Samples', 'Total Cost (ETB)', 'Cost/Sample']]
            table_data.extend(cost_scenarios)

            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.darkred),
                ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('GRID', (0,0), (-1,-1), 1, colors.black)
            ]))
            self.story.append(table)