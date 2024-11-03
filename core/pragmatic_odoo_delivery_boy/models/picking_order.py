from odoo import api, models, fields, tools
import json
import requests
import googlemaps
import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError, ValidationError


class picking_order(models.Model):
    _name = "picking.order"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _rec_name = "sale_order"
    _description = "Picking Order"

    def _default_stage(self):
        warehouse_id = self.env.context.get('default_warehouse_id')
        if not warehouse_id:
            return False
        return self.env['order.stage'].search([('warehouse_ids', '=', warehouse_id)], order="sequence", limit=1).id

    active = fields.Boolean('Active',default=True)
    delivery_boy = fields.Many2one('res.partner','Delivery Boy',domain="[('is_driver', '=', True),('status','=','available')]")
    # assigned_date = fields.datetime('Assigned Date')
    sale_order = fields.Many2one('sale.order','Order')
    invoice = fields.Many2one('account.move','Invoice')
    picking = fields.Many2one('stock.picking', 'Picking')
    assigned_date = fields.Datetime("Assigned Date",default=fields.Datetime.now)
    partner_id = fields.Many2one(related='sale_order.partner_id', string="Partner name")
    state = fields.Selection([
        ('created', 'Unassigned order'),
        ('failed_delivery', 'Failed delivery'),
        ('assigned', 'Assigned to driver'),
        ('accept','Accepted By Driver'),
        ('in_progress', 'In Progress'),
        ('picked','Picked'),
        # ('reject','Rejected By Driver'),
        ('paid', 'Paid by Customer'),
        ('delivered', 'Delivered'),
        ('payment_collected', 'Payment Collected'),
        ('canceled', 'Cancelled')
    ], string='Status', readonly=True, copy=False, index=True, default='created', group_expand='_expand_groups', tracking=True)
    payment = fields.Selection([
        ('unpaid', 'UnPaid'),
        ('paid', 'Paid'),
    ], string='Payment Status', readonly=True, copy=False, index=True, default='unpaid', tracking=True)

    distance_btn_2_loc = fields.Float("Distance in KM", copy=False)
    zip_code = fields.Char("Zip Code", copy=False)

    # payment_collection = fields.Boolean("Payment Collected") remove field
    order_source = fields.Selection([('sale', 'Sale'), ('pos', 'POS')], string="Order Source", default="sale", readonly=True)

    #Point of sale home delivery order fields
    pos_order_id = fields.Many2one('pos.order', 'Order')
    name = fields.Char(string='Order', required=False, readonly=True, copy=False)
    # partner_id = fields.Many2one('res.partner', string='Customer', change_default=True, index=True)
    pos_partner_id = fields.Many2one('res.partner', string='Customer', change_default=True, index=True)
    '''used only for display purpose, showing the inputed value of pos'''
    display_delivery_time = fields.Datetime(string='Delivery Time',default=fields.Datetime.now,tracking=True)

    '''
        this is the actual delivery time which is stored in utc format in db,use this field to access the delivery time
    '''
    delivery_time = fields.Datetime(string='Delivery Time',default=fields.Datetime.now,readonly=True)
    street = fields.Char()
    street2 = fields.Char()
    # zip = fields.Char(change_default=True)
    city = fields.Char()
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict',
                               domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict')
    email = fields.Char(string="Email")
    phone = fields.Char(string="Mobile/Phone")
    # delivery_person = fields.Many2one('res.partner', string="Delivery Person",domain="[('is_driver', '=', True)]")
    bank_statement_ids = fields.One2many('pos.payment', 'picking_order_id', string='Payments', readonly=True)
    lines = fields.One2many('picking.order.line', 'picking_order_id', string='Order Lines', readonly=True, copy=True)
    session_id = fields.Many2one('pos.session', string='Session',readonly=True)
    order_date = fields.Datetime(string='Order Date', readonly=True, default=fields.Datetime.now)
    order_ref = fields.Char(string="Order Ref.", readonly=True)
    cashier = fields.Many2one('res.users', string="Cashier")
    order_note = fields.Text()
    # order_source = fields.Selection([('pos','POS')], string="Source", default="pos")
    payment_status_with_driver = fields.Boolean("Payment Status with driver")
    payment_status = fields.Char('Payment Status', default='Pending')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', help="The warehouse in which user belongs to.")
    # distance_btn_2_loc = fields.Float("Distance in KM", copy=False)
    latitude = fields.Char('Latitude')
    longitude = fields.Char('Longitude')
    transaction_id = fields.Many2one('payment.transaction', string='Transaction')
    acquirer_type = fields.Char(default='cash')
    # payment_collection = fields.Boolean("Payment Collected") remove field
    delivery_type = fields.Selection(
        [('home_delivery', 'Home Delivery'), ('take_away', 'Take Away'), ('default', 'Default')])
    stage_id = fields.Many2one('order.stage', string='State', ondelete='restrict', tracking=True, index=True,
                               default=_default_stage, domain="[('warehouse_ids', '=', warehouse_id)]", copy=False)
    back_order = fields.Many2one('stock.picking', 'Back Order Of')
    back_order_boolean = fields.Boolean('Back Order Boolean')


    @api.model
    def _expand_groups(self, state, domain, order):
        states = []
        records = self.search([])
        created_record = records.filtered(lambda r:r.state == 'created')
        if created_record:
            states.append('created')
        failed_record = records.filtered(lambda r:r.state == 'failed_delivery')
        if failed_record:
            states.append('failed_delivery')
        assigned_record = records.filtered(lambda r:r.state == 'assigned')
        if assigned_record:
            states.append('assigned')
        accept_record = records.filtered(lambda r:r.state == 'accept')
        if accept_record:
            states.append('accept')
        picked_record = records.filtered(lambda r:r.state == 'picked')
        if picked_record:
            states.append('picked')
        paid_record = records.filtered(lambda r:r.state == 'paid')
        if paid_record:
            states.append('paid')
        delivered_record = records.filtered(lambda r:r.state == 'delivered')
        if delivered_record:
            states.append('delivered')
        payment_collected_record = records.filtered(lambda r:r.state == 'payment_collected')
        if payment_collected_record:
            states.append('payment_collected')
        canceled_record = records.filtered(lambda r:r.state == 'canceled')
        if canceled_record:
            states.append('canceled')
        return states

    @api.onchange('delivery_boy')
    def _onchange_delivery_boy(self):
        if not self.delivery_boy and self.state in ['assigned', 'accept']:
            self.state = 'created'
            order_stage_id = self.env['order.stage'].search([('action_type', '=', 'ready')])
            if order_stage_id and self.sale_order:
                self.sale_order.write({'stage_id': order_stage_id.id, 'delivery_state': "ready"})

    def action_picking_order_delivered(self):
        vals = {
            'state': 'delivered'
        }
        order_stage_id = self.env['order.stage'].search([('action_type', '=', 'delivered')])
        if order_stage_id:
            vals["stage_id"] = order_stage_id.id
        self.write(vals)

    def action_picking_order_paid(self, invoice_id=None):
        self.write({
            'invoice': invoice_id,
            'payment': 'paid',
            'state': 'paid'
        })

    def action_picking_order_canceled(self):
        self.write({'state': 'canceled'})

    def assignDriver(self):
        active_ids = self.env.context.get('active_ids',[])
        pickings = self.browse(active_ids)
        vals={}
        sale_orders = pickings.mapped('sale_order')
        vals['sale_order'] = sale_orders.ids
        picking_order_wizard= self.env['picking.order.wizard'].create(vals)

        return{
            'type': 'ir.actions.act_window',
            'name': 'Assign Delivery Boy by Zip Code',
            'res_model': 'picking.order.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': picking_order_wizard.id,
            'view_id': self.env.ref('pragmatic_odoo_delivery_boy.assign_driver_wizard', False).id,
            'target': 'new',
        }

    def update_payment_status(self, vals):
        for rec in self:
            if rec.payment != 'paid' and rec.sale_order:
                last_tx = rec.sale_order.transaction_ids.get_last_transaction()
                # todo last_tx.state == 'done' ; do we need to check for transaction state to 'done'?
                if last_tx and last_tx.acquirer_id.journal_id.type != 'cash':
                    vals['payment'] = 'paid'
                    rec.sale_order.delivery_state = 'paid'

    def write(self, vals):
        payment_transaction_obj = self.env['payment.transaction'].browse(self.sale_order.transaction_ids.ids)
        if payment_transaction_obj:
            vals['acquirer_type'] = payment_transaction_obj[0].acquirer_id.journal_id.type
        so_delivery_state = None

        if vals.get('delivery_boy'):
            if self.state == 'created':
                vals['state'] = 'assigned'
                order_stage_id = self.env['order.stage'].search([('action_type', '=', 'progress')])
                if order_stage_id:
                    vals['stage_id'] = order_stage_id.id
                    so_delivery_state = "assigned"

                Param = self.env['res.config.settings'].sudo().get_values()
                if Param.get('whatsapp_instance_id') and Param.get('whatsapp_token'):
                    if self.sale_order.partner_id.country_id.phone_code and self.sale_order.partner_id.mobile:
                        url = 'https://api.chat-api.com/instance' + Param.get('whatsapp_instance_id') + '/sendMessage?token=' + Param.get('whatsapp_token')
                        headers = {
                            "Content-Type": "application/json",
                        }
                        whatsapp_msg_number = self.sale_order.partner_id.mobile
                        whatsapp_msg_number_without_space = whatsapp_msg_number.replace(" ", "");
                        whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace('+' + str(self.sale_order.partner_id.country_id.phone_code), "")
                        delivery_boy_id = self.env['res.partner'].search([('id', '=', vals.get('delivery_boy'))])
                        msg = "Your order " + delivery_boy_id.name + " driver has assigned."

                        tmp_dict = {
                            "phone": "+" + str(self.sale_order.partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
                            "body": msg

                        }
                        response = requests.post(url, json.dumps(tmp_dict), headers=headers)

                        if response.status_code == 201 or response.status_code == 200:
                            _logger.info("\nSend Message successfully")

        # elif vals.get('delivery_boy') != False:
        #     if self.state in ['assigned', 'accept']:
        #         vals['state'] = 'created'
        #         order_stage_id = self.env['order.stage'].search([('action_type', '=', 'ready')])
        #         if order_stage_id:
        #             vals['stage_id'] = order_stage_id.id
        #             so_delivery_state = "ready"

        if 'delivery_person' in vals:
            partner = self.env['res.partner'].browse(int(vals.get('delivery_person'))).ids
            driver_warehouse = self.env['stock.warehouse.driver'].search([('driver_id', 'in', partner)], limit=1)
            if driver_warehouse and driver_warehouse.warehouse_id:
                vals['warehouse_id'] = driver_warehouse.warehouse_id.id
            vals["delivery_boy"] = vals.get("delivery_person")
            del vals["delivery_person"]

        if vals.get("state") == "paid":
            order_stage_id = self.env['order.stage'].search([('action_type', '=', 'payment')])
            if order_stage_id:
                vals['stage_id'] = order_stage_id.id
                so_delivery_state = "paid"
        # some of the stages not updating fix
        if vals.get("stage_id") and self.sale_order:
            self.sale_order.write({'stage_id': vals['stage_id'], 'delivery_state': so_delivery_state})
        self.update_payment_status(vals)

        if 'state' in vals:
            if vals.get('state'):
                order_stage_id = self.env['order.stage'].search([('action_type', '=', vals.get('state'))])
                if order_stage_id:
                    vals['stage_id'] = order_stage_id.id
        res = super(picking_order, self).write(vals)
        return res

    @api.model
    def create(self, vals):
        # pos delivery order patches to create picking order for pos delivery
        if "zip" in vals:
            vals["zip_code"] = vals["zip"]
            del vals["zip"]
        if "partner_id" in vals:
            vals["pos_partner_id"] = vals["partner_id"]
            del vals["partner_id"]
        if "delivery_person" in vals:
            vals["delivery_boy"] = vals["delivery_person"]
            del vals["delivery_person"]
        if vals.get("delivery_state"):
            vals["state"] = vals["delivery_state"]
        context = dict(self.env.context)
        if vals.get('warehouse_id') and not context.get('default_project_id'):
            context['default_warehouse_id'] = vals.get('warehouse_id')
        res = super(picking_order, self.with_context(mail_create_nosubscribe=True)).create(vals)

        # if vals.get('name'):
        #     pos_order = self.env['pos.order'].search([('pos_reference', '=', vals.get('name'))])
        #     if pos_order:
        #         pos_order.pos_delivery_order_ref = res.id
        res.update_payment_status(vals)
        return res

    @api.onchange('display_delivery_time')
    def onchange_deliverytime(self):
        self.delivery_time = self.display_delivery_time


    def in_progress_action(self):
        pos_order = self.env['pos.order'].search([('pos_reference', '=', self.name)])
        vals = {'state': 'in_progress'}
        if pos_order:
            vals["picking"] = pos_order.picking_id.id
            vals["pos_order_id"] = pos_order.id
        self.write(vals)

    def delivered_action(self):
        self.write({'state': 'delivered'})

    def make_payment_action(self):
        if self.name:
            pos_order = self.env['pos.order'].search([('pos_reference', '=', self.name)])
            if not pos_order:
                raise UserError("POS order not found.\n\n Before making payment, you need to validate POS from frontend.")
            elif pos_order:
                if pos_order.payment_ids:
                    if not self.bank_statement_ids:
                        for i in pos_order.payment_ids:
                            if i.name and 'return' not in i.name:
                                i.write({'name': pos_order.name + ': Home Delivery'})
                            elif not i.name:
                                i.write({'name': pos_order.name + ': Home Delivery'})

                        self.write({'bank_statement_ids': [(6, 0, pos_order.payment_ids.ids)],
                                    'state': 'paid',
                                    'pos_order_id': pos_order.id,
                                    'order_ref': pos_order.name})


class PickingOrderLine(models.Model):
    _name = "picking.order.line"
    _description = "Picking Delivery Order Line"

    picking_order_id = fields.Many2one('picking.order', string='Order Ref', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)],
                                 change_default=True)
    price_unit = fields.Float(string='Unit Price', digits=0)
    qty = fields.Float('Quantity', digits='Product Unit of Measure', default=1)


class PosPayment(models.Model):
    _inherit = "pos.payment"

    picking_order_id = fields.Many2one('picking.order', string="POS Delivery Order statement", ondelete='cascade')


class PickingOrderMultipleAssign(models.Model):
    _name = "picking.order.multiple.assign"
    _description = 'Picking Order Multiple Assign'
    
    delivery_boy = fields.Many2one('res.partner', string='Delivery Boy', domain="[('is_driver', '=', True), ('status','=','available')]")
    sale_order_ids = fields.Many2many('picking.order', string='Sale Orders')

    def assign_multiple(self):
        for rec in self.sale_order_ids:
            rec.delivery_boy = self.delivery_boy
            rec.state = 'assigned'
