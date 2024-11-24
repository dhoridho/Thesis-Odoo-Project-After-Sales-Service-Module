
from odoo import fields, models, api, _


class RepairOrder(models.Model):
    _inherit = "repair.order"

    repair_type = fields.Selection([("customer_repair", "Customer Repair"), (
        "internal_repair", "Internal Repair")], string='Repair Type')
