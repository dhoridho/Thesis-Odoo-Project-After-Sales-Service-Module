# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.translate import _


class Flavour(models.Model):
    _name = 'medicament.flavour'
    _description = "Medicament Flavour"

    name = fields.Char()

    _sql_constraints = [
        ('name_acs_medi_flavour_uniq', 'unique (name)', 'The name of the Content must be unique !'),
    ]


class DrugForm(models.Model):
    _name = 'drug.form'
    _description = "Drug Form"

    code = fields.Char()
    name = fields.Char(string='Form', required=True, translate=True)

    _sql_constraints = [('name_uniq', 'UNIQUE(name)', 'Name must be unique!')]


class ACSActiveComp(models.Model):
    _name = 'active.comp'
    _description = "Drug Active Component"

    name = fields.Char(string='Active Component', required=True, translate=True)
    amount = fields.Float(string='Amount of component', help='Amount of component used in the drug (eg, 250 mg) per dose')


class ACSDrugCompany(models.Model):
    _name = 'drug.company'
    _description = "Drug Company"

    name = fields.Char(string='Company Name', required=True, translate=True)
    code = fields.Char()
    partner_id = fields.Many2one('res.partner', 'Partner', ondelete='restrict')


class ACSDrugRoute(models.Model):
    _name = 'drug.route'
    _description = "Drug Route"

    code = fields.Char()
    name = fields.Char(string='Unit', required=True, translate=True)

    _sql_constraints = [('name_uniq', 'UNIQUE(name)', 'Name must be unique!')]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: