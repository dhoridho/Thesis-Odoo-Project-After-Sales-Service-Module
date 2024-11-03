
from odoo import fields, models, api

class PurchaseOrderPartnerCredit(models.TransientModel):
    _name = 'purchase.order.partner.credit'
    _description = 'Purchase Order Partner Credit'

    name = fields.Many2one("purchase.order", "Purchase Order", readonly=True)
    order_partner = fields.Many2one("res.partner", "Vendor", readonly=True)
    vendor_credit_limit = fields.Float(
        'Vendor Credit Limit', readonly=True)
    is_set_vendor_onhold = fields.Boolean(
        'Vendor On Hold (Credit Limit Exceed)')

    total_payable = fields.Float("Total Payable", readonly=True)
    current_order = fields.Float("Current Purchase Order", readonly=True)
    purchase_orders_cnt_amt = fields.Char("Purchase Orders Pending", readonly=True)
    cust_invoice_cnt_amt = fields.Char(
        "Vendor Invoice Pending", readonly=True)

    @api.model
    def default_get(self, fields):
        res = super(PurchaseOrderPartnerCredit, self).default_get(fields)
        if self._context.get('active_id', False) and self._context.get('active_model', False) == 'purchase.order':
            purchase_obj = self.env['purchase.order'].search(
                [('id', '=', self._context.get('active_id'))], limit=1)
            if purchase_obj:
                res = {}
                so_pend = ''
                inv_pend = ''
                ord_cnt = 0
                ord_amt = 0
                inv_cnt = 0
                inv_amt = 0
                res.update({'name': purchase_obj.id})
                res.update({'current_order': purchase_obj.amount_total})
                if purchase_obj.partner_id:
                    res.update({'order_partner': purchase_obj.partner_id.id, 'is_set_vendor_onhold': purchase_obj.partner_id.is_set_vendor_onhold,
                                'total_payable': purchase_obj.partner_id.debit, 'vendor_credit_limit': purchase_obj.partner_id.vendor_purchase_limit})
                so_pend_obj = self.env['purchase.order'].search(
                    [('state', 'not in', ['done', 'cancel']), ('partner_id', '=', purchase_obj.partner_id.id)])
               
                
                inv_pend_obj = self.env['account.move'].search([('move_type','=','out_invoice'),
                    ('payment_state','!=','paid'),('state','not in',['cancel']),('partner_id','=',purchase_obj.partner_id.id )])
                
                
                for rec in so_pend_obj:
                    ord_cnt += 1
                    ord_amt += rec.amount_total
                if ord_cnt > 0:
                    so_pend = str(ord_cnt) + \
                        ' Purchase Order(s) (Amt) : ' + str(ord_amt)
                    res.update({'purchase_orders_cnt_amt': so_pend})
                for rec in inv_pend_obj:
                    inv_cnt += 1
                    inv_amt += rec.amount_total
                if inv_cnt > 0:
                    inv_pend = str(inv_cnt) + \
                        ' Invoice(s) (Amt) : ' + str(inv_amt)
                    res.update({'cust_invoice_cnt_amt': inv_pend})
        return res

    def confirm_purchase_order(self):
        context = dict(self.env.context) or {}
        active_ids = context.get('active_ids')
        purchase_order = self.env['purchase.order'].browse(active_ids)        
        purchase_order.with_context(order_confirm=True).button_confirm()        

    def action_on_hold_purchase_order(self):
        context = dict(self.env.context) or {}
        active_ids = context.get('active_ids')
        purchase_order = self.env['purchase.order'].browse(active_ids)
        if purchase_order:
            purchase_order.partner_id.is_set_vendor_onhold = True
            purchase_order.write({'state' : 'on_hold'})
