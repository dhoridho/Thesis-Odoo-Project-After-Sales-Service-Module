from odoo import fields, models, api, _
class OrgChartExportType(models.TransientModel):
    _name = 'org.chart.export.type'
    _description = "Organization Chart Export Type"

    output_type = fields.Selection(
        selection=[
            ('pdf', 'PDF'),
            ('png', 'PNG')
        ], 
        string='Output Type',
        default='png',
        required=True
    )

    def export_chart(self):
        return True