# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class CountryDomicileCode(models.Model):
    _name = 'country.domicile.code'

    name = fields.Char('Country Domicile Code', required=True)
    country_id = fields.Many2one('res.country', string='Country', required=True)

    @api.model
    def create(self, vals):
        if self.search([('name', '=', vals.get('name')), ('id', '!=', vals.get('id'))]):
            raise ValidationError(_('Code must be unique!'))
        return super(CountryDomicileCode, self).create(vals)

    def write(self, vals):
        res = super(CountryDomicileCode, self).write(vals)
        for rec in self:
            if self.search([('name', '=', rec.name), ('id', '!=', rec.id)]):
                raise ValidationError(_('Code must be unique!'))
        return res