from odoo import _, api, fields, models


class JobEstimateReport(models.TransientModel):
    _inherit = 'job.estimate.report'

    contract_category = fields.Selection(related='job_estimate_id.contract_category', string="Contract Category")

