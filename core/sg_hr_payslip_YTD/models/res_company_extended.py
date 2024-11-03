from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    period_start = fields.Date('Period Start')
    period_end = fields.Date('Period End')
