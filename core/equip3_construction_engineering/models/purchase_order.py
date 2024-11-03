from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


class RequestForQuotations(models.Model):
    _inherit =  'purchase.order'

    is_engineering = fields.Boolean('Engineering', store=True)

    @api.onchange('project')
    def onchange_project_enginerring(self):
        if self.project:
            # self.is_engineering = False
            if self.project.construction_type == 'engineering':
                self.is_engineering = True
            else:
                self.is_engineering = False

class RFQMaterialOrdersMenuLines(models.Model):
    _inherit = 'purchase.order.line'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')

class RFQVariableLine(models.Model):
    _inherit = 'rfq.variable.line'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')

