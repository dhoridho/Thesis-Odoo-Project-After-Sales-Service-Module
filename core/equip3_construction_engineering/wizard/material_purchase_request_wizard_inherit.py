from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import Warning, ValidationError


class PurchaseRequestWizard(models.TransientModel):
    _inherit = 'purchase.request.wizard'

    def prepare_line(self, line):
        res = super(PurchaseRequestWizard, self).prepare_line(line)
        res['finish_good_id'] = line.finish_good_id.id

        return res
    
    def prepare_pr(self, pr_line, warehouse_id):
        res = super(PurchaseRequestWizard, self).prepare_pr(pr_line, warehouse_id)
        res['is_engineering'] = self.pr_wizard_line.mr_id.is_engineering

        return res

class PurchaseRequestWizardLine(models.TransientModel):
    _inherit = 'purchase.request.wizard.line'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')