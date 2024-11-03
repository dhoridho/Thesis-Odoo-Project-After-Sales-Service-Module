from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError


class MaterialRequest(models.Model):
    _inherit = 'material.request'

    is_engineering = fields.Boolean(string="Is Engineering", default=False)

    @api.onchange('project')
    def onchange_project_enginerring(self):
        if self.project:
            # self.is_engineering = False
            if self.project.construction_type == 'engineering':
                self.is_engineering = True
            else:
                self.is_engineering = False

    def prepare_pr_line(self, line, count, qty):
        res = super(MaterialRequest, self).prepare_pr_line(line, count, qty)
        res['finish_good_id'] = line.finish_good_id.id

        return res

class OrdersMaterialRequestLine(models.Model):
    _inherit = 'material.request.line'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')
