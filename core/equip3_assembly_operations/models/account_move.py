from odoo import models, fields,api


class AccountMove(models.Model):
    _inherit = 'account.move'

    assembly_id = fields.Many2one('assembly.production.record', string='Assembly Production', copy=False)
