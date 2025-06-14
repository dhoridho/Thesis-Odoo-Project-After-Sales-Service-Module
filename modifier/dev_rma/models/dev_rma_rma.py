# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle 
#
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime,date, timedelta

class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    is_process_rma = fields.Boolean('IS Process RMA', copy=False)
    
    
class sale_order(models.Model):
    _inherit = 'sale.order'
    
    is_process_rma = fields.Boolean('IS RMA', copy=False)
    rma_count = fields.Integer(
        string='RMA Count',
        compute='_compute_rma_count'
    )

    state = fields.Selection(
        selection_add=[
            ('return_progress', 'Return Progress'),
            ('refunded', 'Refunded'),
            ('return_rejected', 'Return Rejected')
        ],
    )

    def _compute_rma_count(self):
        for order in self:
            order.rma_count = self.env['dev.rma.rma'].search_count([
                ('sale_id', '=', order.id)
            ])

    def action_view_refunds(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('RMA Refunds'),
            'res_model': 'dev.rma.rma',
            'view_mode': 'tree,form',
            'domain': [('sale_id', '=', self.id)],
            'context': {
                'default_sale_id': self.id,
                'default_partner_id': self.partner_id.id,
            }
        }

    def action_refund_canceled_order(self):
        """Create RMA and refund for canceled orders, then open the refund"""
        self.ensure_one()
        if self.state != 'cancel':
            raise UserError(_("This action is only available for canceled orders"))

        # Find the latest suitable picking (done outgoing shipment)
        picking_id = False
        if self.picking_ids:
            # done_pickings = self.picking_ids.filtered(
            #     lambda p: p.state == 'done' and
            #               p.picking_type_id.code == 'outgoing'
            # ).sorted(key=lambda p: p.date_done, reverse=True)
            #
            # if done_pickings:
            #     picking_id = done_pickings[0].id

            latest_picking = self.picking_ids[-1]
            # Check if picking is already linked to an RMA return
            if latest_picking.picking_type_id.code == 'incoming':
                raise UserError(_(
                    "Cannot create refund: The latest delivery %s is already being processed for return"
                ) % latest_picking.name)
            picking_id = latest_picking

        # Create RMA for the canceled order
        rma = self.env['dev.rma.rma'].create({
            'sale_id': self.id,
            'picking_id': picking_id.id,
            'partner_id': self.partner_id.id,
            'email': self.partner_id.email,
            'phone': self.partner_id.phone,
            'subject': _('Refund %s') % self.name,
            'state': 'draft',
        })

        # Add all order lines to RMA as refund items
        for line in picking_id.move_lines:
            if line.sale_line_id and line.sale_line_id.is_process_rma:
                continue
            self.env['dev.rma.line'].create({
                'rma_id': rma.id,
                'move_id': line.id,
                'product_id': line.product_id.id,
                'delivered_qty': line.quantity_done or 0.0,
                'action': 'refund',
            })

        self.state = 'return_progress'
        return {
            'type': 'ir.actions.act_window',
            'name': _('RMA Refund'),
            'res_model': 'dev.rma.rma',
            'res_id': rma.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_server_action_mod_so(self):
        # for order in self:
        #     if order.state == 'cancel':
        #         order.action_refund_canceled_order()
        print('Action Server')


class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    
    def _get_account_computed_account(self,move_id):
        self.ensure_one()
        if not self.product_id:
            return

        fiscal_position = move_id.fiscal_position_id
        accounts = self.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=fiscal_position)
        if move_id.is_sale_document(include_receipts=True):
            # Out invoice.
            return accounts['income']
        elif self.move_id.is_purchase_document(include_receipts=True):
            # In invoice.
            return accounts['expense']
            
    
    # def _dev_invoice_line_val(self,invoice_id,quantity, price =0):
    #     """
    #     Prepare the dict of values to create the new invoice line for a sales order line.
    #
    #     :param qty: float quantity to invoice
    #     """
    #     self.ensure_one()
    #     if price == 0:
    #         price = self.price_unit
    #     val =  {
    #         'display_type': self.display_type,
    #         'sequence': self.sequence,
    #         'name': self.name,
    #         'product_id': self.product_id.id,
    #         'product_uom_id': self.product_uom.id,
    #         'quantity': quantity,
    #         'discount': self.discount,
    #         'price_unit': price,
    #         'tax_ids': [(6, 0, self.tax_id.ids)],
    #         'analytic_account_id': self.order_id.analytic_account_id.id,
    #         'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
    #         'sale_line_ids': [(4, self.id)],
    #         'move_id':invoice_id.id,
    #         'account_id':self._get_account_computed_account(invoice_id).id,
    #     }
    #     return val

class rma_tags(models.Model):
    _name = 'ram.tags'
    _description = 'RMA Tags'
    
    name = fields.Char('Name')
    

class dev_rma_rma(models.Model):
    _name = 'dev.rma.rma'
    _description = 'RMA'
    _order ='name desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    @api.model
    def _get_default_team(self):
        return self.env['crm.team']._get_default_team_id()
        
        
    
    name = fields.Char('Name' , default='/', copy=False)
    date = fields.Date('Date', required="1", default = date.today())
    deadline_date = fields.Date('Expected Closing', default=date.today(), required="1")
    subject = fields.Char('Subject', required="1")
    user_id = fields.Many2one('res.users', string='Salesperson', required="1", default=lambda self: self.env.user)
    team_id = fields.Many2one('crm.team', string='Sales Channel', default=_get_default_team,)
    sale_id = fields.Many2one('sale.order', string='Sale Order', required="1")
    picking_ids = fields.Many2many('stock.picking', string='Sale Pickings')
    picking_id = fields.Many2one('stock.picking', string='Delivery Order', required='1')
    partner_id = fields.Many2one('res.partner', string='Partner', required="1")
    company_id = fields.Many2one('res.company', string='Company', required="1", default=lambda self:self.env.user.company_id.id)
    email = fields.Char('Email')
    phone = fields.Char('Phone')
    notes = fields.Text('RMA Note')
    rma_lines = fields.One2many('dev.rma.line','rma_id', string='RMA Lines')
    
    state = fields.Selection([('draft','Draft'),
                              ('confirm','Confirm'),
                              ('process','Processing'),
                              ('close','Close'),
                              ('reject','Reject')], string='State', default='draft', track_visibility='onchange')
    
    
    priority = fields.Selection(selection=[('0', '0'),
                                           ('1', '1'),
                                           ('2', '2'),
                                           ('3', '3')],
                                        string="Priority")
                                        
                                        
    tags = fields.Many2many('ram.tags', string='Tags')
    reject_reason = fields.Text('Reject Reason', copy=False)
    incoming_id = fields.Many2one('stock.picking', string='Incoming Shipment', copy=False)
    delivery_id = fields.Many2one('stock.picking', string='Picking', copy=False)
    new_sale_id = fields.Many2one('sale.order', string='New Sale Order', copy=False)
    invoice_id = fields.Many2one('account.move', string='Account Invoice', copy=False)
    is_rma_due = fields.Boolean(compute="_check_rma_due", readonly="1")
    responsible_id = fields.Many2one('res.users', string='Responsible', compute="_compute_responsible_id",copy=False, store=True)

    @api.depends('user_id')
    def _compute_responsible_id(self):
        for rma in self:
            rma.responsible_id = rma.user_id
    
    
    @api.depends('deadline_date','state')
    def _check_rma_due(self):
        for rma in self:
            date = datetime.now().date()
            rma.is_rma_due = rma.state in ('draft','confirm') and rma.deadline_date < date


    @api.depends('line_ids')
    def _compute_has_reconciled_entries(self):
        for move in self:
            move.has_reconciled_entries = len(move.line_ids._reconciled_lines()) > 1


    def action_server_action_mod_rma(self):
        # for rec in self:
        #     if rec.state == 'reject':
        #         rec.sale_id.state = 'refund_rejected'
        #     elif rec.state == 'close':
        #         rec.sale_id.state = 'refunded'
        #     elif rec.state in ['draft','confirm', 'process']:
        #         rec.sale_id.state = 'return_progress'

        print('Action Server')


    @api.onchange('sale_id')
    def onchange_sale_id(self):
        if self.sale_id and self.sale_id.picking_ids:
            picking_ids = []
            for picking in self.sale_id.picking_ids:
                if picking.state == 'done':
                    picking_ids.append(picking.id)
            self.picking_ids = [(6,0, picking_ids)]
        else:
            self.picking_ids = [(6,0, [])]
            self.picking_id = False
            
    @api.onchange('picking_id')
    def onchange_picking_id(self):
        if self.picking_id:
            self.partner_id = self.picking_id and self.picking_id.partner_id and self.picking_id.partner_id.id or False
            vals=[]
            for line in self.picking_id.move_lines:
                if line.sale_line_id and line.sale_line_id.is_process_rma:
                    continue
                vals.append((0,0,{
                            'move_id':line.id,
                            'product_id':line.product_id.id,
                            'delivered_qty':line.quantity_done or 0.0,
                            'action':'refund',
                        }))
            self.rma_lines = vals
        else:
            self.partner_id = False
    
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            self.email = self.partner_id and self.partner_id.email or False
            self.phone = self.partner_id and self.partner_id.phone or False
        else:
            self.email = False
            self.phone = False
            
    
    @api.model
    def create(self, vals):
        if vals.get('name',  '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'dev.rma.rma') or '/'
        return super(dev_rma_rma, self).create(vals)
    



    def action_view_invoice(self):
        invoice_id = [self.invoice_id.id]
        action = self.env.ref('account.action_move_out_refund_type').read()[0]
        if invoice_id:
            action['domain'] = [('id', 'in', invoice_id)]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
        
        
        
    def action_view_shipment(self):
        incoming_id = [self.incoming_id.id]
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        if len(incoming_id) > 1:
            action['domain'] = [('id', 'in', incoming_id)]
        elif len(incoming_id) == 1:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = incoming_id[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
    

    def action_view_delivery(self):
        delivery_id = [self.delivery_id.id]
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        if len(delivery_id) > 1:
            action['domain'] = [('id', 'in', delivery_id)]
        elif len(delivery_id) == 1:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = delivery_id[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
    
    
        
    def action_view_sale_order(self):
        sale_order_id = [self.new_sale_id.id]
        action = self.env.ref('sale.action_quotations').read()[0]
        if len(sale_order_id) > 1:
            action['domain'] = [('id', 'in', sale_order_id)]
        elif len(sale_order_id) == 1:
            action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
            action['res_id'] = sale_order_id[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
        
    
    def get_sale_line(self,product_id):
        for line in self.sale_id.order_line:
            if line.product_id.id == product_id.id:
                return line
    
    
    def get_repair_sale_line(self,product_id,move_id,sale_line_ids = []):
        for line in self.sale_id.order_line:
            if line.product_id.id == product_id.id or move_id in line.move_ids.ids:
                if sale_line_ids:
                    if line.id not in sale_line_ids:
                        return line
                else:
                    return line
                
    
    def action_dev_repair_launch_procurment(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        errors = []
        for r_line in self.rma_lines:
            if r_line.action == 'repair':
                line = self.get_repair_sale_line(r_line.product_id,r_line.move_id.id)
                if line:
                    group_id = line.order_id.procurement_group_id
                    if not group_id:
                        group_id = self.env['procurement.group'].create({
                            'name': line.order_id.name, 'move_type': line.order_id.picking_policy,
                            'sale_id': line.order_id.id,
                            'partner_id': line.order_id.partner_shipping_id.id,
                        })
                        line.order_id.procurement_group_id = group_id
                    else:
                        # In case the procurement group is already created and the order was
                        # cancelled, we need to update certain values of the group.
                        updated_vals = {}
                        if group_id.partner_id != line.order_id.partner_shipping_id:
                            updated_vals.update({'partner_id': line.order_id.partner_shipping_id.id})
                        if group_id.move_type != line.order_id.picking_policy:
                            updated_vals.update({'move_type': line.order_id.picking_policy})

                        if updated_vals:
                            group_id.write(updated_vals)

                    values = line._prepare_procurement_values(group_id=group_id)
                    product_qty = r_line.return_qty

                    procurement_uom = r_line.move_id.product_uom
                    quant_uom = r_line.product_id.uom_id
                    get_param = self.env['ir.config_parameter'].sudo().get_param
                    if procurement_uom.id != quant_uom.id and get_param('stock.propagate_uom') != '1':
                        product_qty = r_line.move_id.product_uom._compute_quantity(product_qty, quant_uom, rounding_method='HALF-UP')
                        procurement_uom = quant_uom

                    try:
                        procurements = []
                        procurements.append(self.env['procurement.group'].Procurement(
                r_line.product_id, product_qty, procurement_uom,
                line.order_id.partner_shipping_id.property_stock_customer,
                r_line.product_id.name, line.order_id.name, r_line.rma_id.company_id, values))
                        if procurements:
                            self.env['procurement.group'].run(procurements)
                    except UserError as error:
                        errors.append(error.name)
                if errors:
                    raise UserError('\n'.join(errors))
                    
                new_pick_id = False
                if self.sale_id and self.sale_id.picking_ids:
                    for picking in self.sale_id.picking_ids:
                        if picking.picking_type_id.code == 'outgoing':
                            if new_pick_id:
                                if picking.id > new_pick_id:
                                    new_pick_id = picking.id
                            else:
                                new_pick_id = picking.id
                self.delivery_id = new_pick_id 
        return True
        
        
    
    def action_dev_launch_procurment(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        errors = []
        for r_line in self.rma_lines:
            if r_line.action == 'replace' and r_line.product_id.id == r_line.replace_product_id.id:
                line = self.get_repair_sale_line(r_line.replace_product_id,r_line.move_id.id)
                if line:
                    group_id = line.order_id.procurement_group_id
                    if not group_id:
                        group_id = self.env['procurement.group'].create({
                            'name': line.order_id.name, 'move_type': line.order_id.picking_policy,
                            'sale_id': line.order_id.id,
                            'partner_id': line.order_id.partner_shipping_id.id,
                        })
                        line.order_id.procurement_group_id = group_id
                    else:
                        # In case the procurement group is already created and the order was
                        # cancelled, we need to update certain values of the group.
                        updated_vals = {}
                        if group_id.partner_id != line.order_id.partner_shipping_id:
                            updated_vals.update({'partner_id': line.order_id.partner_shipping_id.id})
                        if group_id.move_type != line.order_id.picking_policy:
                            updated_vals.update({'move_type': line.order_id.picking_policy})
                        if updated_vals:
                            group_id.write(updated_vals)

                    values = line._prepare_procurement_values(group_id=group_id)
                    product_qty = r_line.replace_qty

                    procurement_uom = r_line.move_id.product_uom
                    quant_uom = r_line.product_id.uom_id
                    get_param = self.env['ir.config_parameter'].sudo().get_param
                    if procurement_uom.id != quant_uom.id and get_param('stock.propagate_uom') != '1':
                        product_qty = r_line.move_id.product_uom._compute_quantity(product_qty, quant_uom, rounding_method='HALF-UP')
                        procurement_uom = quant_uom

                    try:
                        procurements = []
                        procurements.append(self.env['procurement.group'].Procurement(
                r_line.replace_product_id, product_qty, procurement_uom,
                line.order_id.partner_shipping_id.property_stock_customer,
                r_line.replace_product_id.name, line.order_id.name, r_line.rma_id.company_id, values))
                        if procurements:
                            self.env['procurement.group'].run(procurements)
                    except UserError as error:
                        errors.append(error.name)
                if errors:
                    raise UserError('\n'.join(errors))
                    
                new_pick_id = False
                if self.sale_id and self.sale_id.picking_ids:
                    for picking in self.sale_id.picking_ids:
                        if picking.picking_type_id.code == 'outgoing':
                            if new_pick_id:
                                if picking.id > new_pick_id:
                                    new_pick_id = picking.id
                            else:
                                new_pick_id = picking.id
                self.delivery_id = new_pick_id 
        return True

    def action_create_shipment(self):
        # Check if there are any lines with delivered_qty > 0 that need shipment
        lines_with_delivery = self.rma_lines.filtered(lambda l: l.delivered_qty > 0 and l.return_qty > 0)

        if not lines_with_delivery:
            # No actual delivery to return, skip shipment creation
            return True

        wizard_pool = self.env['stock.return.picking']
        pro_vals = []
        for line in lines_with_delivery:
            pro_vals.append((0, 0, {
                'move_id': line.move_id.id,
                'product_id': line.product_id.id,
                'quantity': line.return_qty or 0.0,
                'uom_id': line.move_id.product_uom.id,
                'to_refund': True,
            }))

        if pro_vals:  # Only create shipment if there are valid lines
            vals = {
                'picking_id': self.picking_id.id,
                'parent_location_id': self.picking_id.location_id.location_id.id,
                'original_location_id': self.picking_id.location_id and self.picking_id.location_id.id or False,
                'location_id': self.picking_id.location_id and self.picking_id.location_id.id or False,
                'product_return_moves': pro_vals,
            }
            wizard_id = wizard_pool.create(vals)
            refund = wizard_id.create_returns()
            self.incoming_id = refund.get('res_id')
            self.incoming_id.rma_id = self.id
        return True
        
    def action_create_sale_order(self):
        new_sale_id = False
        for line in self.rma_lines:
            if line.action == 'replace' and line.product_id.id != line.replace_product_id.id:
                if not new_sale_id:
                    new_sale_id = line.rma_id.sale_id.copy()
                    new_sale_id.order_line = False
                    
                if new_sale_id:
                    line_vals = {
                        'product_id':line.replace_product_id.id,
                        'name':line.replace_product_id.name,
                        'product_uom_qty':line.replace_qty,
                        'product_uom':line.replace_product_id and line.replace_product_id.uom_id and line.replace_product_id.uom_id.id or False,
                        'price_unit':line.replace_product_id.lst_price or 0.0,
                        'customer_lead':0.0,
                        'order_id':new_sale_id and new_sale_id.id or False,
                    }
                    sale_line_id = self.env['sale.order.line'].create(line_vals)
                    sale_line_id.product_id_change()
                    sale_line_id.product_uom_qty = line.replace_qty
                    
        self.new_sale_id = new_sale_id and new_sale_id.id or False
        
    
    
    # def action_create_refund_invoice(self):
    #     invoice_id = False
    #     for r_line in self.rma_lines:
    #         if r_line.action == 'refund' or (r_line.action == 'replace' and r_line.product_id.id !=  r_line.replace_product_id.id):
    #             r_line_product_id = r_line.product_id
    #             r_line_qty = r_line.return_qty
    #
    #             if self.sale_id:
    #                 if not self.sale_id.invoice_ids:
    #                     raise ValidationError(_("Please Create Invoice For %s Sale Order for refund")% self.sale_id.name)
    #                 if not invoice_id:
    #                     inv_val = self.sale_id._prepare_invoice()
    #
    #                     if inv_val:
    #                         origin = inv_val.get('origin')
    #                         if origin:
    #                             origin = origin + ' : '+ self.name
    #                         else:
    #                             origin = self.name
    #                         inv_val.update({
    #                             'type':'out_refund',
    #                             'origin':origin,
    #                         })
    #                         invoice_id = self.env['account.move'].create(inv_val)
    #                 # if invoice_id:
    #                 #     vals = []
    #                 #     sale_line = self.get_sale_line(r_line_product_id)
    #                     # if not sale_line.invoice_lines:
    #                     #     raise ValidationError(_("Create invoice for %s product in %s sale order")% (sale_line.product_id.name, self.sale_id.name))
    #                     # if sale_line:
    #                     #     val = _dev_invoice_line_val(invoice_id, r_line_qty)
    #                     #     vals.append((0,0,val))
    #                     #     invoice_id.invoice_line_ids = vals
    #     if invoice_id:
    #         invoice_id._onchange_invoice_line_ids()
    #         self.invoice_id = invoice_id and invoice_id.id or False
    #     return True
        
        
    def action_confirm(self):
        for line in self.rma_lines:
            line.check_deliverqty_returnqty()
        self.action_create_shipment() # create shipment for all product
        self.state = 'confirm'
    

    def action_draft(self):
        self.state = 'draft'
    

    def is_make_refund(self):
        for line in self.rma_lines:
            if line.action == 'refund':
                return True
            if line.action == 'replace' and line.replace_product_id.id != line.product_id.id:
                return True
        return False
    
    # def make_refund(self):
    #     wizard_id = self.env['dev.credit.note.wizard'].create({'sale_id': self.sale_id.id,'rma_id':self.id})
    #     line_pool = self.env['credit.note.product.lines']
    #     sale_line_ids =[]
    #     for line in self.rma_lines:
    #         sale_line=False
    #         if line.action == 'refund':
    #             sale_line = self.get_repair_sale_line(line.product_id, line.move_id.id,sale_line_ids)
    #         elif line.action == 'replace' and line.replace_product_id.id != line.product_id.id:
    #             sale_line = self.get_repair_sale_line(line.product_id, line.move_id.id, sale_line_ids)
    #
    #         if sale_line and sale_line.id not in sale_line_ids:
    #             # if not sale_line.invoice_lines:
    #             #     raise ValidationError(_("Invoice not create For %s Sale Order line")% sale_line.name)
    #             sale_line_ids.append(sale_line.id)
    #             line_pool.create({
    #                 'product_id':sale_line.product_id.id,
    #                 'quantity':line.return_qty,
    #                 'price':sale_line.price_unit,
    #                 'sale_line_id':sale_line and sale_line.id or False,
    #                 'credit_note_id':wizard_id.id,
    #             })
    #
    #     return {
    #         'view_mode': 'form',
    #         'res_id': wizard_id.id,
    #         'res_model': 'dev.credit.note.wizard',
    #         'view_type': 'form',
    #         'type': 'ir.actions.act_window',
    #         'context': self._context,
    #         'target': 'new',
    #     }
    
    
    def dev_process_rma(self):
        self.action_dev_launch_procurment() # create delivery order when replace with same product
        self.action_dev_repair_launch_procurment() # create delivery order when repair 
        self.action_create_sale_order()  # create sale order when replace with other product 
        self.state = 'process'
        for r_line in self.rma_lines:
            if r_line.move_id and r_line.move_id.sale_line_id:
                r_line.move_id.sale_line_id.is_process_rma = True
        
        if self.sale_id:
            sale_process = True
            for line in self.sale_id.order_line:
                if not line.is_process_rma:
                    sale_process = False
            
            if sale_process and self.sale_id:
                self.sale_id.is_process_rma = True
        
    def action_process(self):
        for line in self.rma_lines:
            if line.action == 'replace':
                if not line.replace_product_id:
                    raise ValidationError(_("Please Select Replace Product in Replace Action"))
        
        self.dev_process_rma()
        
    def action_reject(self):
        if self.incoming_id:
            self.incoming_id.action_cancel()
            self.incoming_id.unlink()
        self.state = 'reject'
    
    def action_close(self):
        self.state = 'close'
        
        

class dev_rma_line(models.Model):
    _name = 'dev.rma.line'
    _description = 'RMA Line'
    
    move_id = fields.Many2one('stock.move', string='Move')
    product_id = fields.Many2one('product.product', string='Product', required="1")
    delivered_qty = fields.Float('Delivered Qty', required="1")
    return_qty = fields.Float('Return Qty')
    rma_id = fields.Many2one('dev.rma.rma', string='RMA')
    action = fields.Selection([('refund','Refund'),('repair','Repair'),('replace','Replace')], string='Action', default='refund')
    replace_product_id = fields.Many2one('product.product', string='Rep. Product')
    replace_qty = fields.Float('Quantity')

    def check_deliverqty_returnqty(self):
        for line in self:
            # Allow zero delivery quantity - no validation needed for this case
            if line.delivered_qty == 0:
                # For zero delivery qty, return qty should also be 0 or we skip validation
                if line.return_qty > 0:
                    # This might be a refund case without actual delivery
                    pass  # Allow this scenario
                continue

            # For non-zero delivery quantities, apply normal validation
            if line.delivered_qty > 0:
                if line.return_qty <= 0:
                    raise ValidationError(_("Return Quantity must be positive when there is delivered quantity"))

                if line.return_qty > line.delivered_qty:
                    raise ValidationError(_("Return Quantity must be less or equal to Delivered Quantity"))
    


