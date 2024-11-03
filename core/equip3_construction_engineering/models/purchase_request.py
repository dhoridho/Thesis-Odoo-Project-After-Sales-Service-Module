from odoo import models, fields, api, _
from datetime import datetime


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    is_engineering = fields.Boolean('Engineering')

    @api.onchange('project')
    def onchange_project_enginerring(self):
        if self.project:
            # self.is_engineering = False
            if self.project.construction_type == 'engineering':
                self.is_engineering = True
            else:
                self.is_engineering = False


class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')


class VariableLine(models.Model):
    _inherit = 'pr.variable.line'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')
