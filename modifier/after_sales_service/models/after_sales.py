from odoo import models, fields, api


class AfterSales(models.Model):
    _name = 'after.sales'

    name = fields.Char('Name')
