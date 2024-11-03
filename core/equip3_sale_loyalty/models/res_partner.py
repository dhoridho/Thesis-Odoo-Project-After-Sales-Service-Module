from odoo import models,fields,api,_
from operator import itemgetter

class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer_target_id = fields.Many2one(comodel_name='customer.target', string='Customer Target', readonly=True)
    customer_voucher_ids = fields.One2many(comodel_name='customer.voucher', inverse_name='customer_id', string='Vouchers')
    customer_voucher_count = fields.Integer(string='Customer Voucher Count', compute="_compute_customer_voucher_count", compute_sudo=True)
    target_amount_customer_target = fields.Monetary('Target Amount Customer Target', related='customer_target_id.target_amount')
    level_applied = fields.Integer("Level", related='customer_target_id.level_applied', store=True)
    remaining_amount_cust_target = fields.Float("Amount")
    done = fields.Boolean("Done")
    have_voucher = fields.Boolean("Have Voucher", compute='_compute_customer_voucher_count', store=True)

    @api.depends('customer_voucher_ids')
    def _compute_customer_voucher_count(self):
        for i in self:
            i.customer_voucher_count = len(i.customer_voucher_ids)
            if i.customer_voucher_ids:
                i.have_voucher = True
            else:
                i.have_voucher = False
    
    
    def action_open_customer_voucher(self):
        action = {
                'name': _('Customer Voucher'),
                'view_mode': 'tree,form',
                'res_model': 'customer.voucher',
                'type': 'ir.actions.act_window',
                'target': 'self',
                'domain':[('customer_id','=',self.id)]
            }
        return action

    def update_customer_target(self):
        self.ensure_one()
        if self.customer_target_id:
            if not self.customer_target_id.expired and not self.done:
                self.env.cr.execute("""
                            SELECT id
                            FROM sale_order
                            WHERE partner_id = %s AND date_order >= %s AND date_order <= %s AND state = 'sale' AND (already_used_for_vouchers = False OR already_used_for_vouchers is Null)""", (self.id, self.customer_target_id.start_date.strftime("%Y%m%d"), self.customer_target_id.end_date.strftime("%Y%m%d")))
                sale_ids = self.env.cr.dictfetchall()
                sale_ids = list(map(itemgetter('id'), sale_ids))
                sale_untaxed_amount = 0
                if sale_ids:
                    self.env.cr.execute("""
                                SELECT sum(amount_untaxed)
                                FROM sale_order
                                WHERE id in %s""", [tuple(sale_ids)])
                    sale_untaxed_amount = self.env.cr.dictfetchall()
                    sale_untaxed_amount = sale_untaxed_amount[0]['sum']
                target_amount = self.customer_target_id.target_amount
                voucher_to_create_count = sale_untaxed_amount // target_amount
                remaining_amount = sale_untaxed_amount % target_amount
                # print("====TEST INI sisa amount = ",sale_untaxed_amount, "- (", target_amount, " * ", voucher_existing_count)
                # print("====TEST INI voucher to create count =",target_amount, " : ", int(sisa_amount/target_amount), "Hasilnya sama dengan = ", voucher_to_create_count)
                if voucher_to_create_count:
                    for i in range(0,int(voucher_to_create_count)):
                        state = self.customer_target_id.end_date < fields.Date.today() and 'expired' or 'available'
                        voucher_id = self.env['customer.voucher'].create({
                            'customer_id':self.id,
                            'customer_target_id':self.customer_target_id.id,
                            'state':state,
                            'creation_date':fields.Date.today()
                        })
                    if self.customer_target_id.voucher_type == 'single':
                        self.done = True
                    self.remaining_amount_cust_target = remaining_amount
                    if sale_ids:
                        self._cr.execute("""UPDATE sale_order SET already_used_for_vouchers = True WHERE id in %s""", [tuple(sale_ids)])
                        self._cr.commit()