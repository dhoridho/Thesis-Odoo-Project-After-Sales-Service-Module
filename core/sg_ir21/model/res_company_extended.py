from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    house_no = fields.Char("House No")
    unit_no = fields.Char("Unit No")
