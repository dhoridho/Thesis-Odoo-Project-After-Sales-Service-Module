# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PropertyFacility(models.Model):
    _name = 'property.facility'
    _description = 'Property Facility Service'

    name = fields.Char("Name", required=True)


class PartialPayment(models.Model):
    _name = 'partial.payment'
    _description = 'Partial Payment'

    name = fields.Char("Name", required=True)
    number_of_pay = fields.Integer("#Partial Payment", required=True)

    @api.model
    def create(self, vals):
        if vals['number_of_pay'] <= 0:
            raise UserError(_("Please enter valid # Payments"))
        res = super(PartialPayment, self).create(vals)
        return res


class PropertyType(models.Model):
    _name = 'property.type'
    _description = 'Property Type'

    name = fields.Char("Name", required=True)
