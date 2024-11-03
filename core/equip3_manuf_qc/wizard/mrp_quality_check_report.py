from odoo import models, fields


class MrpQualityCheckReportWizard(models.TransientModel):
    _inherit = 'mrp.quality.check.report'

    is_plan = fields.Boolean('Is Plan')
    is_consumption = fields.Boolean('Is Consumption')

