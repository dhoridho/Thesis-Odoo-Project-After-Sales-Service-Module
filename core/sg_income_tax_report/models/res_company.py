from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    organization_id_type = fields.Selection([
        ('7', 'UEN – Business Registration number issued by ACRA'),
        ('8', 'UEN – Local Company Registration number issued by ACRA'),
        ('A', 'ASGD – Tax Reference number assigned by IRAS'),
        ('I', 'ITR – Income Tax Reference number assigned by IRAS'),
        ('U', 'UENO – Unique Entity Number Others')],
        string='Organization ID Type')
    organization_id_no = fields.Char('Organization ID No')
