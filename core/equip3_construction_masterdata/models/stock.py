from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class InheritWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    project = fields.Many2one ('project.project', string="Project", Store="1")

class InheritLocation(models.Model):
    _inherit = 'stock.location'

    project = fields.Many2one ('project.project', string="Project", Store="1")
