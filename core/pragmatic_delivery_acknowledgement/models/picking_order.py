from odoo import api, models, fields, tools
import string, random
from datetime import datetime


class picking_order(models.Model):
    _inherit = "picking.order"

    def _compute_broadcast(self):
        Param = self.env['ir.config_parameter'].sudo()
        if Param.get_param('pragmatic_delivery_control_app.is_broadcast_order'):
            self.broadcast = True
        else:
            self.broadcast = False

    customer_code = fields.Char(string="Customer Acknoledgement Code")
    delivery_boy_code = fields.Char(string="Delivery Boy Acknoledgement Code")
    picking_id = fields.Many2one('stock.picking',string="Deliveryboy Picking")
    is_broadcast_order = fields.Boolean(string="Broadcast Order")
    broadcast = fields.Boolean(string="Broadcast",compute="_compute_broadcast")
    currency_id = fields.Many2one('res.currency',string="Currency", related='sale_order.currency_id')

    @api.model
    def create(self,vals):
        res = super(picking_order, self).create(vals)
        # ack_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        Param = self.env['ir.config_parameter'].sudo()
        if Param.get_param('pragmatic_delivery_control_app.is_delivery_acknowledgement'):
            ack_code = ''.join(random.choices(string.digits, k=5))
            res.customer_code = ack_code

            msg = ("<p> Dear Sir / Madam,</p> <p>Your Order delivery acknowledge code is %s</p> <p>Thank You</p>" % ack_code)
            template = self.env['ir.model.data'].get_object('pragmatic_delivery_acknowledgement', 'delivery_acknowledgement_email_template')

            template.body_html = msg
            template.send_mail(res.id, force_send=True)
        return res

    def assign_driver(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Assign Delivery Boy',
            'res_model': 'picking.order.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'context':{'default_sale_order':[(4,self.sale_order.id)]},
            'view_id': self.env.ref('pragmatic_odoo_delivery_boy.assign_driver_wizard', False).id,
            'target': 'new',
        }

    def pick_delivery(self, qty_done):
        """
        this process happen after the delivery of order completed by delivery boy from the website.
        it is make done picking if 'Enable Delivery Boy Location' is not enable
        it is create a new picking for delivery boy and make transfer like
            store location -> delivery boy location
            delivery boy location -> customer
        """
        # delivery_boy_store_configuration = self.user_has_groups('pragmatic_delivery_control_app.group_delivery_boy_store_configuration')
        picking = self.picking
        sale_order = self.env['sale.order'].search([('id', '=', self.sale_order.id)])

        picking.action_assign()
        # if not delivery_boy_store_configuration:
        #     if self.picking.state == 'assigned':
        #         for move in picking.move_lines.filtered(lambda m: m.state not in ['done', 'cancel']):
        #             for move_line in move.move_line_ids:
        #                 move_line.qty_done = move_line.product_uom_qty
        #         picking.with_context(skip_immediate=True).button_validate()
        # else:
        picking_type_obj = self.env['stock.picking.type'].sudo()
        delivery_boy_location = self.env['delivery.boy.store'].sudo().search([('delivery_boy_id.partner_id','=',self.delivery_boy.id)])
        deliveryboy_picking_id = picking.copy()
        picking_type_id = picking_type_obj.sudo().search([('id', '=', picking.picking_type_id.id)])
        deliveryboy_picking_id.picking_type_id = picking_type_id.id
        deliveryboy_picking_id.action_assign()
        deliveryboy_picking_id.location_id = delivery_boy_location.location_id.id
        # deliveryboy_picking_id.move_ids_without_package.initial_demand = sale_order.order_line.product_uom_qty
        deliveryboy_picking_id.move_ids_without_package.product_uom_qty = qty_done
        deliveryboy_picking_id.move_ids_without_package.quantity_done = qty_done
        for move in deliveryboy_picking_id.move_lines.filtered(lambda m: m.state not in ['done', 'cancel']):
            for move_line in move.move_line_ids:
                move_line.location_id = delivery_boy_location.location_id.id
                move_line.location_dest_id = deliveryboy_picking_id.location_dest_id.id
        self.picking_id = deliveryboy_picking_id.id
        self.picking_id.move_ids_without_package.initial_demand = sale_order.order_line.product_uom_qty
        # deliveryboy_picking_id.with_context(skip_immediate=True).button_validate()
        # self.sale_order.write({'state':'picked'})
        # self.picking_id = deliveryboy_picking_id.id
        # print('self.picking_idself.picking_idself.picking_id',self.picking_id)
        picking.location_dest_id = deliveryboy_picking_id.location_id.id
        picking.move_ids_without_package.initial_demand = sale_order.order_line.product_uom_qty
        for move in picking.move_lines.filtered(lambda m: m.state not in ['done', 'cancel']):
            for move_line in move.move_line_ids:
                move_line.location_id = picking.location_id.id
                move_line.location_dest_id = deliveryboy_picking_id.location_id.id
                move_line.qty_done = qty_done
        picking.with_context(skip_immediate=True).button_validate()
        stock_picking = self.env['stock.picking'].search([('id', '=', picking.id)], limit=1)
        stock_picking.write({'state': 'done'})
        self.state = 'picked'
        # order_stage_id = self.env['order.stage'].sudo().search([('action_type', '=', 'picked')])
        # if order_stage_id:
        #     self.stage_id = order_stage_id.id

        """
            reconsile invoice
        """

        # move_obj = self.env['account.move'].sudo()
        # invoice_id = self.sale_order.invoice_ids
        # store_config_id = self.env['store.configuration'].sudo().search(
        #     [('location_id', '=', self.picking.location_id.id)])
        # if store_config_id and invoice_id:
        #     line_ids = [(0, 0, {
        #         'partner_id': self.delivery_boy.id,  # delivery boy id,
        #         'account_id': store_config_id.delivery_boy_account_id.id,
        #         'journal_id': store_config_id.delivery_boy_journal_id.id,
        #         'name': 'Cash received by delivery boy from order Number {0}'.format(self.sale_order.name),
        #         'amount_currency': 0.0,
        #         'debit': invoice_id.amount_total,
        #         'credit': 0.0,
        #     }),
        #                 (0, 0, {
        #                     'partner_id': invoice_id.partner_id.id,
        #                     'account_id': invoice_id.partner_id.property_account_receivable_id.id,
        #                     'journal_id': store_config_id.delivery_boy_journal_id.id,
        #                     'name': 'Cash received by delivery boy from order Number {0}'.format(self.sale_order.name),
        #                     'amount_currency': 0.0,
        #                     'debit': 0.0,
        #                     'credit': invoice_id.amount_total,
        #                 })]

        #     vals = {
        #         'journal_id': store_config_id.delivery_boy_journal_id.id,
        #         'ref': 'Cash received by delivery boy from order Number {0}'.format(self.sale_order.name),
        #         'narration': 'Delivery Boy Receipt',
        #         'date': datetime.now(),
        #         'line_ids': line_ids,
        #     }
        #     journal_id = move_obj.create(vals)
        #     journal_id.sudo().action_post()
        #     self.delivery_boy_move_id = journal_id.id

        #     line_1 = journal_id.line_ids.filtered(lambda line: line.account_id.user_type_id.type == 'receivable')
        #     line_2 = invoice_id.line_ids.filtered(lambda line: (line.account_id.user_type_id.type == 'receivable'))
        #     (line_1 + line_2).reconcile()

        # if invoice_id:
        #     self.action_picking_order_paid(invoice_id.id)

        # """
        #     create invoice for order
        # """
        # if not self.sale_order.invoice_count:
        #     invoice_obj = self.sale_order._create_invoices()
        #     invoice_obj.action_post()
        #     self.invoice = invoice_obj.id

    def order_delivered(self):
        picking = self.picking_id
        picking.with_context(skip_immediate=True).button_validate()

        order_stage_id = self.env['order.stage'].sudo().search([('action_type', '=', 'picked')])
        if order_stage_id:
            self.stage_id = order_stage_id.id
        move_obj = self.env['account.move'].sudo()
        invoice_id = self.sale_order.invoice_ids
        store_config_id = self.env['store.configuration'].sudo().search(
            [('location_id', '=', self.picking.location_id.id)])
        if store_config_id and invoice_id:
            order_stage_id = self.env['order.stage'].sudo().search([('action_type', '=', 'delivered')])
            self.sudo().write({'state':'delivered'})
            self.sudo().write({'stage_id' : order_stage_id.id})
            # print('storeeeeeeeeeeeeeeeee', picking.id)
            # line_ids = [(0, 0, {
            #     'partner_id': self.delivery_boy.id,  # delivery boy id,
            #     'account_id': store_config_id.delivery_boy_account_id.id,
            #     'journal_id': store_config_id.delivery_boy_journal_id.id,
            #     'name': 'Cash received by delivery boy from order Number {0}'.format(self.sale_order.name),
            #     'amount_currency': 0.0,
            #     'debit': invoice_id.amount_total,
            #     'credit': 0.0,
            # }),
            #             (0, 0, {
            #                 'partner_id': invoice_id.partner_id.id,
            #                 'account_id': invoice_id.partner_id.property_account_receivable_id.id,
            #                 'journal_id': store_config_id.delivery_boy_journal_id.id,
            #                 'name': 'Cash received by delivery boy from order Number {0}'.format(self.sale_order.name),
            #                 'amount_currency': 0.0,
            #                 'debit': 0.0,
            #                 'credit': invoice_id.amount_total,
            #             })]

            # vals = {
            #     'journal_id': store_config_id.delivery_boy_journal_id.id,
            #     'ref': 'Cash received by delivery boy from order Number {0}'.format(self.sale_order.name),
            #     'narration': 'Delivery Boy Receipt',
            #     'date': datetime.now(),
            #     'line_ids': line_ids,
            # }
            # journal_id = move_obj.create(vals)
            # journal_id.sudo().action_post()
            # self.delivery_boy_move_id = journal_id.id
            # print(1/0)

            # line_1 = journal_id.line_ids.filtered(lambda line: line.account_id.user_type_id.type == 'receivable')
            # line_2 = invoice_id.line_ids.filtered(lambda line: (line.account_id.user_type_id.type == 'receivable'))
            # (line_1 + line_2).reconcile()

        if invoice_id:
            order_stage_id = self.env['order.stage'].sudo().search([('action_type', '=', 'delivered')])
            self.sudo().write({'state':'delivered'})
            self.sudo().write({'stage_id' : order_stage_id.id})
            # self.action_picking_order_paid(invoice_id.id)

        """
            create invoice for order
        """
        if not self.sale_order.invoice_count:
            order_stage_id = self.env['order.stage'].sudo().search([('action_type', '=', 'delivered')])
            self.sale_order.sudo().write({'stage_id' : order_stage_id.id})
            invoice_obj = self.sale_order._create_invoices()
            # invoice_obj.action_post()
            self.invoice = invoice_obj.id
            subtotal = 0
            total = 0
            picking_order_obj = self.env['picking.order'].search([('id','=', self.id)])
            for rec in picking_order_obj:
                if rec.state in ['picked','paid','delivered','payment_collect']:
                    for move in rec.picking_id.move_ids_without_package:
                        for sale in rec.sale_order.order_line:
                            if move.product_id.id == sale.product_id.id and sale.tax_id:
                                subtotal = subtotal + ((move.quantity_done * sale.price_unit) + (move.quantity_done * sale.price_unit * sale.tax_id.amount / 100))
                            if move.product_id.id == sale.product_id.id and not sale.tax_id:
                                subtotal = subtotal + (move.quantity_done * sale.price_unit)
                            total += subtotal
                rec.order_amount = total

    def print_invoice(self):
        self.ensure_one()
        if self.sale_order.invoice_ids:
            action = self.sale_order.invoice_ids.action_invoice_print()
            # action.update({'close_on_report_download': True})
            return action

    def check_deliveryboy_code(self,deliveryboy_code):
        if self.customer_code == deliveryboy_code:
            self.delivery_boy_code = deliveryboy_code
            return True
        else:
            return False

    def delivery_order_ready(self):
        self.is_broadcast_order = True

    @api.model
    def get_stock_count(self, product_id, location_id):
        if location_id and product_id:
            stock_qty = self.env['stock.quant'].sudo().search([('location_id', '=', int(location_id)), ('product_id', '=', int(product_id))])
            product_available_qty = sum(stock_qty.mapped("available_quantity"))
            return product_available_qty