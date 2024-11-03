from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    carry_forward_end_date = fields.Date('Carry Forward End Date')
