from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    @api.model
    def create(self, vals):
        res = super(AccountMove,self).create(vals)
        if vals.get("agreement_id"):
            agreement = self.env["agreement"].browse(vals.get("agreement_id"))
            # self.property_id = agreement.property_id.id
            res.property_id = agreement.property_id.id
        return res

class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
    def action_post(self):
		
        active_id = self._context.get('active_id')
        invoice_id = self.env['account.move'].browse(active_id)
        agreement = self.env["agreement"].search([('id','=',invoice_id.agreement_id.id)])
        if agreement:
            for each in agreement:
                property_id = each.property_id.id
                if property_id:
                    property = self.env["product.product"].search([('id','=',property_id)])
                    if property.user_commission_ids:
                        for comm in property.user_commission_ids:
                            values = {}
                            values.update({'pay_reference':invoice_id.payment_reference,'payment_origin':self.name,'user_id' :comm.user_id.id,'property_id':property_id,'percentage':comm.percentage,'commission':(invoice_id.amount_total * comm.percentage)/100,'inv_pay_source':invoice_id.name, 'invoice_id':invoice_id.id})
                            commission_id=self.env['commission.line'].create(values)
                            # print('commission_id======',commission_id)
                            commission_id.write({'name':self.env['ir.sequence'].next_by_code('commission.line') or _('New')})
        res = super(AccountPayment, self).action_post()
        return res
