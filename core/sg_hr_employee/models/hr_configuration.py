from odoo import fields, models


class HrEmployeeConfiguration(models.TransientModel):
    _inherit = 'res.config.settings'

    module_sg_document_expiry = fields.Boolean(
        string="Manage Expire Document Details With Report",
        help="This help to send mail for document expire with report")
