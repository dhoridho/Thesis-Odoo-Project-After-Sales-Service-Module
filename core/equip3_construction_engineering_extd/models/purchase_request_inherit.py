from odoo import models, fields, api
from odoo.exceptions import ValidationError,UserError

class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'
    
    def prepare_line_wiz(self, rec):
        res = super(PurchaseRequest, self).prepare_line_wiz(rec)
        res['finish_good_id'] = rec.finish_good_id.id

        return res
    
    def send_data_var(self, line_id):
        res = super(PurchaseRequest, self).send_data_var(line_id)
        res['finish_good_id'] = line_id.finish_good_id.id

        return res
    
    # def send_data_var_det(self, record, line):
    #     res = super(PurchaseRequest, self).send_data_var_det(record, line)
    #     res['finish_good_id'] = line.finish_good_id.id

    #     return res