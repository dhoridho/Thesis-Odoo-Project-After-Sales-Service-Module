from odoo import models,fields,api,_

class ApplyVoucher(models.Model):
    _name = 'apply.voucher'
    _rec_name = 'customer_id'
    _description = "Apply Voucher"

    customer_id = fields.Many2one('res.partner', string='Customer')
    voucher_ids = fields.One2many('customer.voucher', string='Vouchers', compute='_compute_voucher_ids')    

    @api.onchange('voucher_ids')
    def onchange_voucher_ids(self):
        single_vouchers = self.voucher_ids.filtered(lambda v: v.customer_voucher_type == 'single')
        multi_vouchers = self.voucher_ids.filtered(lambda v: v.customer_voucher_type == 'multi')

        if single_vouchers and any(single_vouchers.mapped('is_apply_voucher')):
            selected_vouchers = single_vouchers.filtered(lambda v: v.is_apply_voucher)
            for voucher in single_vouchers:
                if voucher.is_apply_voucher:
                    voucher.write({'is_apply_voucher': True})
                else:
                    voucher.write({'is_apply_voucher': False})
            if len(selected_vouchers) > 1:
                first_selected_voucher = selected_vouchers[0]
                unselected_vouchers = selected_vouchers - first_selected_voucher
                unselected_vouchers.write({'is_apply_voucher': False})

            if multi_vouchers:
                multi_vouchers.write({'is_apply_voucher': False})

        if multi_vouchers and any(multi_vouchers.mapped('is_apply_voucher')):
            selected_vouchers = multi_vouchers.filtered(lambda v: v.is_apply_voucher)
            selected_vouchers.write({'is_apply_voucher': True})
            if single_vouchers:
                single_vouchers.write({'is_apply_voucher': False})


    def check_all(self):
        multi_vouchers = self.voucher_ids.filtered(lambda v: v.customer_voucher_type == 'multi')

        if multi_vouchers:
            multi_vouchers.write({'is_apply_voucher': True})
        elif not multi_vouchers:
            pass
        active_id = self._context.get('active_id')
        view_id = self.env.ref('equip3_sale_loyalty.apply_voucher_view_wizard_form').id
        apply_voucher = self.env['apply.voucher'].create({
            'customer_id': self.customer_id.id,
            'voucher_ids': [(6, 0, self.customer_id.customer_voucher_ids.filtered(lambda v: v.state == 'available').ids)]
        })
        return {
            'name': 'Apply Voucher',
            'type': 'ir.actions.act_window',
            'res_model': 'apply.voucher',
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': view_id,
            'target': 'new',
            'res_id': apply_voucher.id,
            'context': {'active_id': active_id}
        }

        

    def apply_voucher(self):
        selected_vouchers = self.voucher_ids.filtered(lambda v: v.is_apply_voucher)
        active_id = self._context.get('active_id')
        order = self.env['sale.order'].browse(active_id)
        # old_order = self.env['sale.order'].browse(self._context.get('active_id'))
        line_ids = []
        cashback_line_ids = []
        for voucher in selected_vouchers:
            customer_target = voucher.customer_target_id
            reward_type = customer_target.reward_type
            reward_product = voucher.discount_line_product_id
            disc_type = customer_target.disc_type
            if reward_type == 'discount':
                if disc_type == 'fix':
                    disc_amount = customer_target.disc_amount
                    vals_line = {
                        'sale_line_sequence': str(len(order.order_line) + 1),
                        'product_id': reward_product.id,
                        'price_unit': -customer_target.disc_amount,
                        'product_uom_qty': 1,
                        'name': reward_product.name,
                        'product_uom': reward_product.uom_id.id,
                        'account_tag_ids': [(6, 0, order.account_tag_ids.ids)],
                        'delivery_address_id': order.partner_id.id,
                        'customer_voucher_id': voucher.id,
                    }
                    line_ids.append((0,0,vals_line))
                else:
                    untaxed_amount = order.amount_untaxed
                    disc_amount = untaxed_amount*customer_target.disc_percentage/100
                    vals_line = {
                        'sale_line_sequence': str(len(order.order_line) + 1),
                        'product_id': reward_product.id,
                        'price_unit': -disc_amount,
                        'product_uom_qty': 1,
                        'name': reward_product.name,
                        'product_uom': reward_product.uom_id.id,
                        'account_tag_ids': [(6, 0, order.account_tag_ids.ids)],
                        'delivery_address_id': order.partner_id.id,
                        'customer_voucher_id': voucher.id,
                    }
                    line_ids.append((0,0,vals_line))
                voucher.state = 'used'
            elif reward_type == 'product':
                sequence = len(order.order_line) + 1
                price = 0
                for line in customer_target.free_product_line_ids:
                    order_line = order.order_line.filtered(lambda x: x.product_id.id == line.product_id.id)
                    price += (line.product_id.product_tmpl_id.list_price * line.quantity)
                    if not order_line:
                        vals = {
                            'sale_line_sequence': str(sequence),
                            'product_id': line.product_id.id,
                            'price_unit': line.product_id.product_tmpl_id.list_price,
                            'product_uom_qty': line.quantity,
                            'name': line.description,
                            'product_uom': line.uom_id.id,
                            'account_tag_ids': [(6, 0, order.account_tag_ids.ids)],
                            'delivery_address_id': order.partner_id.id,
                            'customer_voucher_id': voucher.id,
                            'tax_id':[(5,0,0)],
                        }
                        sequence += 1
                        order.order_line = [(0, 0, vals)]
                    else:
                        order_line.product_uom_qty += line.quantity
                order_line = order.order_line.filtered(lambda x: x.product_id.id == customer_target.discount_line_product_id.id)
                if not order_line:
                    vals = {
                        'sale_line_sequence': str(sequence),
                        'product_id': customer_target.discount_line_product_id.id,
                        'price_unit': -(price),
                        'product_uom_qty': 1,
                        'name': customer_target.discount_line_product_id.name,
                        'product_uom': customer_target.discount_line_product_id.uom_id.id,
                        'account_tag_ids': [(6, 0, order.account_tag_ids.ids)],
                        'delivery_address_id': order.partner_id.id,
                        'customer_voucher_id': voucher.id,
                        'tax_id':[(5,0,0)],
                    }
                    order.order_line = [(0, 0, vals)]
                else:
                    order_line.product_uom_qty += 1
                voucher.state = 'used'
            elif reward_type == 'cashback':
                line_yang_product_nya_sama = False
                if customer_target.apply_cashback == 'percentage':
                    disc_amount = customer_target.discount_line_product_id.lst_price / 100 * order.amount_total
                else:
                    disc_amount = customer_target.discount_line_product_id.lst_price
                free_qty = customer_target.quantity or 1
                total = disc_amount * free_qty
                if cashback_line_ids:
                    if cashback_line_ids[-1][2]['product_id'] == customer_target.discount_line_product_id.id and cashback_line_ids[-1][2]['price_unit'] == customer_target.discount_line_product_id.lst_price:
                        line_yang_product_nya_sama = True
                if not line_yang_product_nya_sama:
                    vals_line = {
                        'sequence': str(len(cashback_line_ids) + 1),
                        'product_id': customer_target.discount_line_product_id.id,
                        'name': customer_target.discount_line_product_id.name,
                        'product_uom_qty': free_qty,
                        'price_unit': disc_amount,
                        'total': total,
                        'customer_voucher_id': voucher.id,
                    }
                    cashback_line_ids.append((0,0,vals_line))
                else:
                    cashback_line_ids[-1][2]['product_uom_qty'] += free_qty
                    cashback_line_ids[-1][2]['total'] += disc_amount * free_qty
                voucher.state = 'used'
        if line_ids:
            order.order_line = line_ids
        if cashback_line_ids:
            order.cashback_line_ids = [(6,0,[])]
            order.cashback_line_ids = cashback_line_ids
            order.show_cashback = True
        if selected_vouchers:
            order.customer_voucher_used_ids = [(6,0,selected_vouchers.ids)]
     
        return {'type': 'ir.actions.act_window_close'}

    # def apply_alls(self):
    #     for rec in self:
    #         multi_vouchers = rec.env['customer.voucher'].search([('customer_voucher_type', '=', 'multi'), 
    #                                                                 ('id', 'in', rec.voucher_ids.ids)])
    #         multi_vouchers.write({'is_apply_voucher': True})
    #         return {}


    # customer_voucher_ids = fields.One2many(comodel_name='customer.voucher', inverse_name='customer_id', string='Vouchers')
    # customer_apply_id = fields.Many2one(comodel_name='res.partner', string='Customer')
    # customer_voucher_state = fields.Selection(string='Voucher State', related='customer_voucher_ids.state')
    # customer_voucher_type = fields.Selection(string='Voucher Type', related='customer_voucher_ids.customer_voucher_type')

    


    @api.depends('customer_id')
    def _compute_voucher_ids(self):
        for wizard in self:
            voucher_ids = self.env['customer.voucher'].search([
                ('customer_id', '=', wizard.customer_id.id),
                ('state', '=', 'available'),
            ])
            wizard.voucher_ids = [(6, 0, voucher_ids.ids)]
            # wizard.voucher_ids = voucher_ids
        # selected_vouchers = self.voucher_ids.filtered(lambda v: v.is_apply_voucher)
        # selected_vouchers.write({'is_apply_voucher': False})
        