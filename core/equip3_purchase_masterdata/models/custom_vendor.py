from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _description = 'Res Partner'

    def write(self, values):
        res = super(ResPartner, self).write(values)
        for i in self:
            if i.company_size > i.company_size2:
                raise UserError('Company Size invalid')

        return res

    @api.model
    def create(self, values):
        res = super(ResPartner, self).create(values)

        if self.company_size > self.company_size2:
            raise UserError('Company Size invalid')

        return res
