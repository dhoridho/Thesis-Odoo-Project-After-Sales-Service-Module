# -*- coding: utf-8 -*-

import pytz
from datetime import datetime
from odoo import api, fields, models, tools, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_is_zero

class PosOrder(models.Model):
    _inherit = "pos.order"

    pos_order_day = fields.Char('Day')
    pos_order_hour = fields.Float('Time')
    hour_group_id = fields.Many2one('hour.group','Hour Group')
    promotion_ids = fields.Many2many(
        'pos.promotion',
        'pos_order_promotion_rel',
        'order_id',
        'promotion_id',
        string='Promotions')

    total_mdr_amount_customer = fields.Float('Total MDR Amount (Customer)',copy=False)
    total_mdr_amount_company = fields.Float('Total MDR Amount (Company)',copy=False)
    is_self_picking = fields.Boolean('Self Picking',copy=False)
    rounding_payment = fields.Float(string='Rounding Payment', digits=0, copy=False)
    voucher_id = fields.Many2one('pos.voucher', 'Voucher Used')
    voucher_amount = fields.Float('Voucher Used (Amount)')
    active = fields.Boolean('Active',default=True)

    is_payment_method_with_receivable = fields.Boolean('Is Payment Method with Receivable?')
    receivable_invoice_count = fields.Integer('Receivable Invoice Count', compute='_compute_receivable_invoice_count')

    state = fields.Selection(selection_add=[('partially paid', 'Partially paid'),])
    payment_paid = fields.Float('Payment Paid', compute='_compute_payment_paid')
    zone_id = fields.Many2one('pos.zone','Zone')
    is_home_delivery = fields.Boolean('Home Delivery',copy=False)
    is_pre_order = fields.Boolean('Pre-Order',copy=False)
    estimated_order_pre_order = fields.Date('Estimated Order Pre-Order',copy=False)
    total_before_discount = fields.Monetary('Total w/o Discount',compute='_compute_all_total_order')
    total_discount = fields.Monetary('Discount',compute='_compute_all_total_order')
    total_after_discount = fields.Monetary('Total w Discount',compute='_compute_all_total_order')
    total_after_discount_w_o_tax = fields.Monetary('Total w Discount w/o tax',compute='_compute_all_total_order')
    is_use_pos_coupon = fields.Boolean('Is Use POS Coupon?') 
    pos_coupon_id = fields.Many2one('pos.coupon', string='POS Coupon', compute='_compute_pos_coupon_id')


    def _compute_all_total_order(self):
        for data in self:
            total_before_discount = 0
            total_discount = 0
            total_after_discount = 0
            total_after_discount_w_o_tax = 0

            for l in data.lines:
                total_before_discount+= l.price_unit * l.qty
                total_discount+= l.discount_amount_percent
                total_after_discount+= l.untax_amount
                total_after_discount_w_o_tax+= l.untax_amount

            data.total_before_discount = total_before_discount
            data.total_discount = total_discount
            data.total_after_discount = total_after_discount
            data.total_after_discount_w_o_tax = total_after_discount_w_o_tax


    @api.model
    def _order_fields(self, ui_order):
        order_fields = super(PosOrder, self)._order_fields(ui_order)
        if ui_order.get('voucher_id', False):
            order_fields.update({
                'voucher_id': ui_order['voucher_id'],
                'voucher_amount': ui_order['voucher_amount'],
            })
        if ui_order.get('generate_voucher_id'):
            order_fields.update({'generate_voucher_id': ui_order['generate_voucher_id'] })
        if ui_order.get('is_use_pos_coupon'):
            order_fields.update({ 'is_use_pos_coupon': ui_order['is_use_pos_coupon'] })

        #TODO: Check if employee exist in the db
        employee_id = self.env['hr.employee'].search([('id','=',ui_order.get('employee_id')), ('user_id','=',ui_order.get('user_id'))], limit=1)
        if not employee_id:
            employee_id = self.env['hr.employee'].search([('user_id','=', ui_order.get('user_id'))], limit=1)
        if employee_id:
            ui_order['employee_id'] = employee_id.id
            order_fields['employee_id'] = employee_id.id
        else:
            ui_order['employee_id'] = False
            order_fields['employee_id'] = False
            
        return order_fields

    @api.model
    def create(self,vals):
        product_product_obj = self.env['product.product'].sudo()
        # Check for existing order to avoid duplicates
        generate_voucher_id = vals.get('generate_voucher_id')
        if generate_voucher_id:
            del vals['generate_voucher_id']
        if vals.get('pos_reference') and vals.get('state') != 'return':
            pos_reference = vals.get('pos_reference').replace('Order ', '')
            amount_total = float(vals.get('amount_total', 0))
            domain = [('pos_reference','=',pos_reference), ('amount_total','=',amount_total)]
            existing_order = self.search(domain, limit=1)
            if existing_order:
                return existing_order


        if vals.get('lines'):
            count = 0
            for pos_o_l in vals['lines']:
                if vals.get('is_exchange_order') and vals.get('exchange_amount'):
                    if pos_o_l[2]['qty'] < 0 and not pos_o_l[2]['is_product_exchange']:
                        pos_o_l[2]['qty'] = pos_o_l[2]['qty'] * -1
                # pos_orderline_product_rec = product_product_obj.search_read([('id','=',pos_orderline_product_id)],['is_can_be_po'])
                # if pos_orderline_product_rec:
                #     del vals['lines'][count]
                count+=1
                
        res = super(PosOrder,self).create(vals)
        if res.date_order:
            user_tz = self.env.user.tz or pytz.utc
            local = pytz.timezone(user_tz)
            dt = pytz.utc.localize(datetime.strptime(str(res.date_order),DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local) 
            curr_week_day = dt.strftime('%A')
            ord_time = dt.hour+dt.minute/60.0
            hour_group = self.env['hour.group'].search([('start_hour','<=',ord_time),('end_hour','>=',ord_time)],limit=1)
            res.pos_order_hour = dt.hour+dt.minute/60.0
            if curr_week_day:
                res.pos_order_day = curr_week_day
            if hour_group:
                res.hour_group_id = hour_group.id
        order = res
        if order.voucher_id:
            if order.voucher_id.apply_type == 'percent':
                order.voucher_id.write({'state': 'used', 'use_date': fields.Datetime.now()})
                self.env['pos.voucher.use.history'].create({
                    'pos_order_id': order.id,
                    'voucher_id': order.voucher_id.id,
                    'value': order.voucher_amount,
                    'used_date': fields.Datetime.now(),
                    'cashier_id': self.env.user.id
                })
            else:
                amount = order.voucher_amount
                if (order.voucher_id.value - amount) <= 0:
                    order.voucher_id.write({
                        'state': 'used',
                        'use_date': fields.Datetime.now(),
                        'value': 0,
                    })
                else:
                    order.voucher_id.write({'value': (order.voucher_id.value - amount)})
                self.env['pos.voucher.use.history'].create({
                    'pos_order_id': order.id,
                    'cashier_id': self.env.user.id,
                    'voucher_id': order.voucher_id.id,
                    'value': amount,
                    'used_date': fields.Datetime.now()
                })

        if generate_voucher_id:
            self.env['generate.pos.voucher.use.history'].create({
                'pos_order_id': order.id,
                'cashier_id': self.env.user.id,
                'voucher_id':generate_voucher_id,
                'value':0,
                'used_date': fields.Datetime.now()
            })

        if vals.get('is_use_pos_coupon') and order.pos_coupon_id:
            self.env['pos.coupon.use.history'].create({
                'coupon_id': order.pos_coupon_id.id,
                'pos_order_id': order.id,
                'cashier_id': self.env.user.id,
                'used_date': fields.Datetime.now()
            })
            pos_coupon_id = order.pos_coupon_id
            pos_coupon_id.write({ 'write_date': fields.Datetime.now()}) # For auto sync coupon
            if pos_coupon_id.no_of_usage > 0:
                if pos_coupon_id.no_of_used >= pos_coupon_id.no_of_usage:
                    pos_coupon_id.write({ 'active': False, 'state': 'expired' })
        
        for line in order.lines:
            if line.promotion_stack_ids:
                for promotion_stack in line.promotion_stack_ids:
                    if promotion_stack.promotion_id:
                        promotion_stack.promotion_id.write({ 'write_date': fields.Datetime.now()}) # For auto sync promotion

        return res




    @api.model
    def _payment_fields(self, order, ui_paymentline):
        res = super(PosOrder, self)._payment_fields(order, ui_paymentline)
        res['payment_card_id'] = ui_paymentline.get('payment_card_id') or False
        return res

    def _get_fields_exception(self):
        return [
            'creation_time',
            'mp_dirty',
            'mp_skip',
            'quantity_wait',
            'state',
            'tags',
            'quantity_done',
            'promotion_discount_total_order',
            'promotion_discount_category',
            'promotion_discount_by_quantity',
            'promotion_discount',
            'promotion_gift',
            'promotion_price_by_quantity',
        ]


    def set_pack_operation_lot(self, picking=None):
        """Set Serial/Lot number in pack operations to mark the pack operation done."""
        """
        TODO  we foce core odoo because: we get lot id direct pos operation lot \n
        And if order return we dont care lots_necessary, auto add back lot ID
        """

        StockProductionLot = self.env['stock.production.lot']
        PosPackOperationLot = self.env['pos.pack.operation.lot']
        has_wrong_lots = False
        for order in self:
            for move in (picking or self.picking_ids[0]).move_lines:
                picking_type = (picking or self.picking_id).picking_type_id
                lots_necessary = True
                if picking_type:
                    lots_necessary = picking_type and picking_type.use_existing_lots
                qty_done = 0
                pack_lots = []
                pos_pack_lots = PosPackOperationLot.search([
                    ('order_id', '=', order.id),
                    ('product_id', '=', move.product_id.id)
                ])
                if pos_pack_lots and (lots_necessary or order.is_return):
                    for pos_pack_lot in pos_pack_lots:
                        stock_production_lot = StockProductionLot.search([('name', '=', pos_pack_lot.lot_name), ('product_id', '=', move.product_id.id)])
                        if stock_production_lot:
                            # a serialnumber always has a quantity of 1 product, a lot number takes the full quantity of the order line
                            qty = 1.0
                            if stock_production_lot.product_id.tracking == 'lot':
                                qty = abs(pos_pack_lot.pos_order_line_id.qty)
                            qty_done += qty
                            if pos_pack_lot.lot_id:
                                pack_lots.append({
                                    'lot_id': pos_pack_lot.lot_id.id,
                                    'qty': qty,
                                    'lot_name': pack_lot.lot_id.name
                                })
                            else:
                                pack_lots.append({
                                    'lot_id': stock_production_lot.id,
                                    'qty': qty,
                                    'lot_name': stock_production_lot.name
                                })
                        else:
                            has_wrong_lots = True
                elif move.product_id.tracking == 'none' or not lots_necessary:
                    qty_done = move.product_uom_qty
                else:
                    has_wrong_lots = True
                for pack_lot in pack_lots:
                    lot_id, qty, lot_name = pack_lot['lot_id'], pack_lot['qty'], pack_lot['lot_name']
                    self.env['stock.move.line'].create({
                        'picking_id': move.picking_id.id,
                        'move_id': move.id,
                        'product_id': move.product_id.id,
                        'product_uom_id': move.product_uom.id,
                        'qty_done': qty,
                        'location_id': move.location_id.id,
                        'location_dest_id': move.location_dest_id.id,
                        'lot_id': lot_id,
                        'lot_name': lot_name,
                    })
                if not pack_lots and not float_is_zero(qty_done, precision_rounding=move.product_uom.rounding):
                    if len(move._get_move_lines()) < 2:
                        move.quantity_done = qty_done
                    else:
                        move._set_quantity_done(qty_done)
        return has_wrong_lots

    def _compute_receivable_invoice_count(self):
        result = {}
        if self.ids:
            query = """
                SELECT pos_order_id, count(id)
                FROM account_move
                WHERE pos_order_id IN (%s)
                GROUP BY pos_order_id
            """ % (str(self.ids)[1:-1])
            self._cr.execute(query)
            result = dict(self._cr.fetchall())

        for rec in self:
            rec.receivable_invoice_count = result.get(rec.id, 0)

    def action_view_receivable_invoices(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_out_invoice_type')
        action['context'] = {
            'default_move_type': 'out_invoice', 
            'is_ppn_invisible': True, 
            'def_invisible': False
        }
        action['domain'] = [('pos_order_id', '=', self.id),]
        return action

    def _compute_payment_paid(self):
        for rec in self:
            payment_ids = rec.payment_ids.filtered(lambda l: not l.payment_method_id.is_receivables)
            rec.payment_paid = sum(payment_ids.mapped('amount'))

    def _compute_pos_coupon_id(self):
        for rec in self:
            pos_coupon_id = False
            for line in rec.lines:
                if line.pos_coupon_id:
                    pos_coupon_id = line.pos_coupon_id
                    break
            rec.pos_coupon_id = pos_coupon_id

    def get_pos_order_backend_link(self):
        self.ensure_one()
        action_id = self.env.ref('point_of_sale.action_pos_pos_form').sudo().id
        menu_id = self.env.ref('point_of_sale.menu_point_ofsale').sudo().id
        return f'/web#action={action_id}&id={self.id}&menu_id={menu_id}&model=pos.order&view_type=form'

    def _validate_order_for_refund(self):
        self.ensure_one()
        return True

    # OVERRIDE
    def refund(self):
        """Create a copy of order  for refund order"""
        refund_orders = self.env['pos.order']
        for order in self:
            order._validate_order_for_refund()
            # When a refund is performed, we are creating it in a session having the same config as the original
            # order. It can be the same session, or if it has been closed the new one that has been opened.
            current_session = order.session_id.config_id.current_session_id
            if not current_session:
                # TODO: allow other user to Return Order from Backend
                current_sessions = order.session_id.config_id.session_ids.filtered(lambda s: not s.state == 'closed' and not s.rescue)
                if current_sessions:
                    current_session = current_sessions[0]
            
            if not current_session:
                raise UserError(_('To return product(s), you need to open a session in the POS %s', order.session_id.config_id.display_name))
            data_copy = order._prepare_refund_values(current_session)
            data_copy['name'] = 'RETURN/'+order.name
            refund_order = order.copy(
                data_copy
            )

            refund_order_ref = f'{refund_order.name}({refund_order.id})'
            message_log = f'<div class="pos_return_order _op"><div><b>Refund Products</b></div><div>Refund Order Ref: {refund_order_ref}</div></div>'
            order.message_post(body=message_log, message_type='notification')

            for line in order.lines:
                PosOrderLineLot = self.env['pos.pack.operation.lot']
                for pack_lot in line.pack_lot_ids:
                    PosOrderLineLot += pack_lot.copy()
                line.copy(line._prepare_refund_data(refund_order, PosOrderLineLot))

            refund_orders |= refund_order

        return {
            'name': _('Return Products'),
            'view_mode': 'form',
            'res_model': 'pos.order',
            'res_id': refund_orders.ids[0],
            'view_id': False,
            'context': self.env.context,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    # OVERRIDE
    def action_receipt_to_customer(self, name, client, ticket):
        if not self:
            return False
        if not client.get('email'):
            return False

        message = _("<p>Dear %s,<br/>Here is your electronic ticket for the %s. </p>") % (client['name'], name)
        filename = 'Receipt-' + name + '.jpg'
        receipt = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': ticket,
            'res_model': 'pos.order',
            'res_id': self.ids and self.ids[0] or False,
            'store_fname': filename,
            'mimetype': 'image/jpeg',
        })
        mail_values = {
            'subject': _('Receipt %s', name),
            'body_html': message,
            'author_id': self.env.user.partner_id.id,
            'email_from': self.env.company.email or self.env.user.email_formatted,
            'email_to': client['email'],
            'attachment_ids': [(4, receipt.id)],
        }

        if self.mapped('account_move'):
            if self.ids:
                report = self.env.ref('point_of_sale.pos_invoice_report')._render_qweb_pdf(self.ids[0])
                filename = name + '.pdf'
                attachment = self.env['ir.attachment'].create({
                    'name': filename,
                    'type': 'binary',
                    'datas': base64.b64encode(report[0]),
                    'store_fname': filename,
                    'res_model': 'pos.order',
                    'res_id': self.ids[0],
                    'mimetype': 'application/x-pdf'
                })
                mail_values['attachment_ids'] += [(4, attachment.id)]

        mail = self.env['mail.mail'].sudo().create(mail_values)
        mail.send()



class POSOrderLine(models.Model):
    _inherit = "pos.order.line"

    promotion = fields.Boolean('Applied Promotion', readonly=1)
    promotion_id = fields.Many2one('pos.promotion', 'Promotion', readonly=1, ondelete="set null")
    promotion_reason = fields.Char(string='Promotion Reason', readonly=1)

    coupon_program_id = fields.Many2one(
        'coupon.program',
        'Coupon Program',
        readonly=1
    )
    coupon_id = fields.Many2one(
        'coupon.coupon',
        'Coupon',
        readonly=1
    )
    coupon_ids = fields.Many2many(
        'coupon.coupon',
        'coupon_coupon_gift_card_rel',
        'pos_line_id',
        'coupon_id',
        string='Gift Cards',
        readonly=1
    )
    discount_amount_percent = fields.Float(string='Discount Amount', digits=0, default=0.0)
    discount_from_pricelist = fields.Float(string='Discount From Pricelist', digits=0, default=0.0)
    all_discount_except_pricelist = fields.Float(string='All Discount Except Pricelist', digits=0, default=0.0)
    tax_amount = fields.Float("Tax Amount", digits=0, default=0.0)
    untax_amount = fields.Float("Untax Amount", digits=0, default=0.0)
    total_price = fields.Float("Total Price", digits=0, default=0.0)
    unit_price_pricelist = fields.Float('Unit Price (Pricelist)',copy=False,default=0)
    active = fields.Boolean('Active',default=True)
    zone_id = fields.Many2one('pos.zone','Zone')
    promotion_stack_ids = fields.One2many('pos.order.line.promotion', 'pos_order_line_id', string='Promotions')
    pos_coupon_id = fields.Many2one('pos.coupon', string='POS Coupon')
    pos_coupon_reward_description = fields.Char('POS Coupon Reward Description')

    def _order_line_fields(self, line, session_id=None):
        values = super(POSOrderLine, self)._order_line_fields(line, session_id)

        if line[2].get('all_total_discount', None):
            values[2].update({'discount_amount_percent': line[2].get('all_total_discount', 0)})
        if line[2].get('unit_price_pricelist', None):
            values[2].update({'unit_price_pricelist': line[2].get('unit_price_pricelist', 0)})
        if line[2].get('discount_from_pricelist', None):
            values[2].update({'discount_from_pricelist': line[2].get('discount_from_pricelist', 0)})
        if line[2].get('all_discount_except_pricelist', None):
            values[2].update({'all_discount_except_pricelist': line[2].get('all_discount_except_pricelist', 0)})

        # Sales Person
        if line[2].get('session_info', None):
            session_info = line[2].get('session_info', {})
            if session_info.get('user') and 'id' in session_info.get('user', {}):
                values[2].update({ 'user_id': session_info['user']['id'] })

        # Coupon(pos.coupon)
        if line[2].get('pos_coupon_id') and line[2].get('is_product_coupon_reward') == True:
            values[2].update({'full_product_name': 'Coupon Service'})

        # Promotion Stack
        promotion_stack_ids = []
        promotion_stack = line[2].get('promotion_stack')
        if promotion_stack:
            for promotion_id in promotion_stack:
                promotion = promotion_stack[promotion_id]
                data = promotion['data']
                if data:
                    promotion_stack_id = self.env['pos.order.line.promotion'].create({
                        'sequence': promotion['id'] + promotion['sequence'],
                        'promotion_id': promotion['id'],
                        'promotion_disc': promotion['discount'],
                        'price': data['price'],
                        'amount': data['amount'],
                        'amount_percentage': data['amount_percentage'],
                    })
                    promotion_stack_ids += [promotion_stack_id.id]
        if promotion_stack_ids:
           values[2].update({ 'promotion_stack_ids': [(4, p_id) for p_id in promotion_stack_ids] })

        return values

    @api.model
    def create(self, vals):
        tax_obj = self.env['account.tax']
        po_line = super(POSOrderLine, self).create(vals) 
        if po_line.coupon_id:
            coupon = po_line.coupon_id
            if not coupon.is_gift_card or (coupon.is_gift_card and coupon.balance_amount <= 0):
                if not coupon.is_gift_card:
                    self.env['coupon.coupon'].browse(vals.get('coupon_id')).write({
                        'state': 'used',
                        'pos_order_id': vals.get('order_id'),
                    })
                else:
                    self.env['coupon.coupon'].browse(vals.get('coupon_id')).write({
                        'state': 'used',
                    })
        company = po_line.company_id
        total_price = 0
        if po_line.price_unit and po_line.qty:
            total_price = po_line.price_unit * po_line.qty
            
        po_line.write({
            'total_price':total_price,
        })
        
        if po_line.price_unit:
            if company.tax_discount_policy == 'untax':
                value_tax = po_line.tax_ids_after_fiscal_position.compute_all(po_line.price_unit * po_line.qty, po_line.order_id.currency_id, 1, False, False)
                subtotal = po_line.price_unit * po_line.qty
                discount_amount_percent = tax_amount = untax_amount = 0
                discount_amount_percent = po_line.discount_amount_percent
                untax_amount =subtotal-discount_amount_percent
                tax_amount = po_line.price_subtotal_incl -  po_line.price_subtotal
                
                po_line.write({
                    'tax_amount':tax_amount,
                    'untax_amount':untax_amount,
                })
            else:
                value_tax = po_line.tax_ids_after_fiscal_position.compute_all(po_line.price_unit * po_line.qty, po_line.order_id.currency_id, 1, False, False)
                subtotal = po_line.price_unit * po_line.qty
                total_excluded = value_tax.get('total_excluded') or subtotal
                total_included = value_tax.get('total_included') or subtotal
                discount_amount_percent = tax_amount = untax_amount = 0
                discount_amount_percent = po_line.discount_amount_percent
                tax_amount = total_included - total_excluded
                untax_amount = po_line.price_unit * po_line.qty
                if value_tax:
                    taxes = value_tax['taxes']
                    for t in taxes:
                        tax_data = tax_obj.browse(t['id'])
                        if tax_data.price_include:
                            untax_amount-=t['amount']
                po_line.write({
                    'tax_amount':tax_amount,
                    'untax_amount':untax_amount,
                })
        return po_line

    def action_open_promotion_stack(self):
        self.ensure_one()
        context = self._context.copy()
        context['form_view_ref'] = 'equip3_pos_masterdata.promotion_stack_pos_order_line_form_view'
        action = {
            'name': _(f'Promotions ({self.order_id.name})'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': self.id,
            'res_model': 'pos.order.line',
            'context': context,
            'target': 'new',
        }
        return action