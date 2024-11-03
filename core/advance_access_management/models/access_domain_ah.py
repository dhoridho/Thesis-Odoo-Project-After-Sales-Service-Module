from odoo import models, fields, api
from odoo.exceptions import Warning, ValidationError, UserError


class access_domain_ah(models.Model):
    _inherit = 'access.domain.ah'

    soft_restrict = fields.Boolean("Soft Restrict")

    @api.onchange('soft_restrict')
    def onchanges_soft_restrict(self):
        for rec in self:
            if not rec.soft_restrict:
                rec.read_right = True
