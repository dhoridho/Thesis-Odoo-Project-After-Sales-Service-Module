from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = "res.company"

    ph_company_no = fields.Char('PH Company No')
    is_ph_bir_accreditation = fields.Boolean('PH BIR Accreditation ?')
    ph_bir_accreditation_no = fields.Char('PH BIR Accreditation Number')
    ph_bir_accreditation_issued_date = fields.Date('PH BIR Accreditation Issued Date')
    ph_bir_accreditation_valid_until = fields.Date('PH BIR Accreditation Valid Until')