
from odoo import api, fields, models, _


class PurchaseTenderCreateWizard(models.TransientModel):
    _inherit = 'purchase.tender.create.wizard'

    def _send_lines(self, product_line_id):
        res = super(PurchaseTenderCreateWizard, self)._send_lines(product_line_id)
        res['finish_good_id'] = product_line_id.finish_good_id.id

        return res
    
    def _create_tender_vals(self):
        res = super(PurchaseTenderCreateWizard, self)._create_tender_vals()
        for record in self:
            for product_line_id in record.product_line_ids:
                purchase_request_id = product_line_id.pr_line_id.request_id
        res['is_engineering'] = purchase_request_id.is_engineering

        return res

class PurchaseTenderCreateLinesWizard(models.TransientModel):
    _inherit = 'purchase.tender.create.lines.wizard'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')
