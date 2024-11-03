from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class SaleOrderReportWizard(models.TransientModel):
    _inherit = 'construction.sale.order.report.wizard'

    contract_category = fields.Selection(related='sale_order_id.contract_category', string="Contract Category")

    