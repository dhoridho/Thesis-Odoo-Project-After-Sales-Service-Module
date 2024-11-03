from odoo import _, api, fields, models



class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    def action_confirm_purchase_request(self):
        if self.mr_id:
            mr_id = self.mr_id[0]
            mr_id._check_processed_record(mr_id.id, self.id)
        return super(PurchaseRequest, self).action_confirm_purchase_request()