from odoo import models,fields,api,_


class PurchaseOrderWizardInherit(models.TransientModel):
    _inherit = 'purchase.order.wizard'

    # OVERRIDE
    sh_create_po = fields.Selection(selection_add=[
        ('pr', 'Purchase Request')
    ], default='rfq', string="Create RFQ/Purchase Order")

    def _domain_partner(self):
        return [('company_id','=',self.env.company.id),('vendor_sequence','!=',False)]
    partner_ids = fields.Many2many(comodel_name='res.partner', string='Vendors', domain=_domain_partner)
    so_id = fields.Many2one(comodel_name='sale.order', string='Source Document')
    is_dropship = fields.Boolean(string='Is Dropship', readonly=True)
    

    def action_create_po_from_so_y(self):
        clean_context = dict(self._context or {})
        context = dict(self._context or {})
        is_goods_orders = is_services_orders = is_assets_orders = False
        purchase_order_line = self.so_id.order_line
        active_id = self.env['purchase.order.line'].sudo().search([('id', 'in', dict(self._context or {}).get('active_ids'))],limit=1)
        order_ids = []
        if purchase_order_line:
            if self.sh_create_po != 'pr':
                if self.env['ir.config_parameter'].sudo().get_param('is_good_services_order') == 'True': 
                    # GOODS ORDER 
                    context = clean_context.copy()
                    context['goods_order'] = True
                    for partner in self.partner_ids:
                        vals = {}
                        po_line = []
                        for order_line in purchase_order_line.filtered(lambda l:l.product_id.type not in ('service','asset')):
                            if not vals:
                                vals = {
                                    'partner_id': partner.id,
                                    'user_id': self.env.user.id,
                                    'origin' : self.so_id.display_name,
                                    'date_order': fields.Datetime.now(),
                                    'date_planned': fields.Datetime.now(),
                                    'picking_type_id': order_line.order_id.warehouse_id.in_type_id.id or False,
                                    'destination_warehouse_id':self.so_id.warehouse_id.id,
                                    'branch_id': order_line.order_id.branch_id.id,
                                    'analytic_account_group_ids': order_line.order_id.account_tag_ids.ids,
                                    'is_goods_orders': True,
                                    'sh_sale_order_id': self.so_id.id,
                                    'is_dropship':self.is_dropship,
                                    'customer_partner_id':self.so_id.partner_id.id,
                                    'customer_location_partner_id':self.so_id.partner_shipping_id.id,
                                    'is_single_delivery_destination':self.is_dropship or self.so_id.is_single_warehouse,
                                    'discount_type': self.so_id.discount_type,
                                    'discount_method': self.so_id.discount_method,
                                    'discount_amount': self.so_id.discount_amount,
                                    'multi_discount': self.so_id.multi_discount
                                }
                            line_vals = {
                                'product_id': order_line.product_id.id,
                                'name': order_line.product_id.name,
                                'status': 'draft',
                                'product_uom': order_line.product_uom.id,
                                'product_qty': order_line.product_qty,
                                'price_unit': order_line.price_unit,
                                'picking_type_id': order_line.order_id.warehouse_id.in_type_id.id,
                                'destination_warehouse_id': order_line.line_warehouse_id_new.id,
                                'analytic_tag_ids': order_line.account_tag_ids.ids,
                                'taxes_id': [(6, 0, order_line.tax_id.ids)],
                                'is_goods_orders':True,
                                'discount_method': order_line.discount_method,
                                'multi_discount': order_line.multi_discount,
                                'discount_amount': order_line.discount_amount,
                                'discounted_value': order_line.discounted_value
                            }
                            po_line.append((0, 0, line_vals))
                        if po_line:
                            purchase_order_id = self.env['purchase.order'].with_context(context).create(vals)
                            purchase_order_id.write({'order_line': po_line})
                            purchase_order_id._onchange_partner_invoice_id()
                            if self.sh_create_po == 'po':
                                purchase_order_id.selected_order = True
                                purchase_order_id.button_confirm()
                            else:
                                purchase_order_id.selected_order = False

                            order_ids.append(purchase_order_id.id)

                    # SERVICES ORDER 
                    context = clean_context.copy()
                    context['services_good'] = True
                    for partner in self.partner_ids:
                        vals = {}
                        po_line = []
                        for order_line in purchase_order_line.filtered(lambda l:l.product_id.type == 'service'):
                            if not vals:
                                vals = {
                                    'partner_id': partner.id,
                                    'user_id': self.env.user.id,
                                    'origin' : self.so_id.display_name,
                                    'date_order': fields.Datetime.now(),
                                    'date_planned': fields.Datetime.now(),
                                    'picking_type_id': order_line.order_id.warehouse_id.in_type_id.id or False,
                                    'destination_warehouse_id':self.so_id.warehouse_id.id,
                                    'branch_id': order_line.order_id.branch_id.id,
                                    'analytic_account_group_ids': order_line.order_id.account_tag_ids.ids,
                                    'is_services_orders': True,
                                    'sh_sale_order_id': self.so_id.id,
                                    'is_dropship':self.is_dropship,
                                    'customer_partner_id':self.so_id.partner_id.id,
                                    'customer_location_partner_id':self.so_id.partner_shipping_id.id,
                                    'is_single_delivery_destination':self.is_dropship or self.so_id.is_single_warehouse,
                                    'discount_type': self.so_id.discount_type,
                                    'discount_method': self.so_id.discount_method,
                                    'discount_amount': self.so_id.discount_amount,
                                    'multi_discount': self.so_id.multi_discount
                                }
                            line_vals = {
                                'product_id': order_line.product_id.id,
                                'name': order_line.product_id.name,
                                'status': 'draft',
                                'product_uom': order_line.product_uom.id,
                                'product_qty': order_line.product_qty,
                                'price_unit': order_line.price_unit,
                                'picking_type_id': order_line.order_id.warehouse_id.in_type_id.id,
                                'destination_warehouse_id': order_line.line_warehouse_id_new.id,
                                'analytic_tag_ids': order_line.account_tag_ids.ids,
                                'taxes_id': [(6, 0, order_line.tax_id.ids)],
                                'is_services_orders':True,
                                'discount_method': order_line.discount_method,
                                'multi_discount': order_line.multi_discount,
                                'discount_amount': order_line.discount_amount,
                                'discounted_value': order_line.discounted_value
                            }
                            po_line.append((0, 0, line_vals))
                        if po_line:
                            # vals['order_line'] = po_line
                            purchase_order_id = self.env['purchase.order'].with_context(context).create(vals)
                            purchase_order_id.write({'order_line': po_line})
                            purchase_order_id._onchange_partner_invoice_id()
                            if self.sh_create_po == 'po':
                                purchase_order_id.selected_order = True
                                purchase_order_id.button_confirm()
                            else:
                                purchase_order_id.selected_order = False

                            order_ids.append(purchase_order_id.id)

                    
                    # ASSETS ORDER 
                    context = clean_context.copy()
                    context['assets_orders'] = True
                    for partner in self.partner_ids:
                        vals = {}
                        po_line = []
                        for order_line in purchase_order_line.filtered(lambda l:l.product_id.type == 'asset'):
                            if not vals:
                                vals = {
                                    'partner_id': partner.id,
                                    'user_id': self.env.user.id,
                                    'origin' : self.so_id.display_name,
                                    'date_order': fields.Datetime.now(),
                                    'date_planned': fields.Datetime.now(),
                                    'picking_type_id': order_line.order_id.warehouse_id.in_type_id.id or False,
                                    'destination_warehouse_id':self.so_id.warehouse_id.id,
                                    'branch_id': order_line.order_id.branch_id.id,
                                    'analytic_account_group_ids': order_line.order_id.account_tag_ids.ids,
                                    'is_assets_orders': True,
                                    'sh_sale_order_id': self.so_id.id,
                                    'is_dropship':self.is_dropship,
                                    'customer_partner_id':self.so_id.partner_id.id,
                                    'customer_location_partner_id':self.so_id.partner_shipping_id.id,
                                    'is_single_delivery_destination':self.is_dropship or self.so_id.is_single_warehouse,
                                    'discount_type': self.so_id.discount_type,
                                    'discount_method': self.so_id.discount_method,
                                    'discount_amount': self.so_id.discount_amount,
                                    'multi_discount': self.so_id.multi_discount
                                }
                            line_vals = {
                                'product_id': order_line.product_id.id,
                                'name': order_line.product_id.name,
                                'status': 'draft',
                                'product_uom': order_line.product_uom.id,
                                'product_qty': order_line.product_qty,
                                'price_unit': order_line.price_unit,
                                'picking_type_id': order_line.order_id.warehouse_id.in_type_id.id,
                                'destination_warehouse_id': order_line.line_warehouse_id_new.id,
                                'analytic_tag_ids': order_line.account_tag_ids.ids,
                                'taxes_id': [(6, 0, order_line.tax_id.ids)],
                                'is_assets_orders':True,
                                'discount_method': order_line.discount_method,
                                'multi_discount': order_line.multi_discount,
                                'discount_amount': order_line.discount_amount,
                                'discounted_value': order_line.discounted_value
                            }
                            po_line.append((0, 0, line_vals))
                        if po_line:
                            # vals['order_line'] = po_line
                            purchase_order_id = self.env['purchase.order'].with_context(context).create(vals)
                            purchase_order_id.write({'order_line': po_line})
                            purchase_order_id._onchange_partner_invoice_id()
                            if self.sh_create_po == 'po':
                                purchase_order_id.selected_order = True
                                purchase_order_id.button_confirm()
                            else:
                                purchase_order_id.selected_order = False

                            order_ids.append(purchase_order_id.id)

                else:
                    # ALL ORDER 
                    for partner in self.partner_ids:
                        vals = {}
                        po_line = []
                        for order_line in purchase_order_line:
                            if not vals:
                                vals = {
                                    'partner_id': partner.id,
                                    'user_id': self.env.user.id,
                                    'origin' : self.so_id.display_name,
                                    'date_order': fields.Datetime.now(),
                                    'date_planned': fields.Datetime.now(),
                                    'picking_type_id': order_line.order_id.warehouse_id.in_type_id.id or False,
                                    'destination_warehouse_id':self.so_id.warehouse_id.id,
                                    'branch_id': order_line.order_id.branch_id.id,
                                    'analytic_account_group_ids': order_line.order_id.account_tag_ids.ids,
                                    'sh_sale_order_id': self.so_id.id,
                                    'is_dropship':self.is_dropship,
                                    'customer_partner_id':self.so_id.partner_id.id,
                                    'customer_location_partner_id':self.so_id.partner_shipping_id.id,
                                    'is_single_delivery_destination':self.is_dropship or self.so_id.is_single_warehouse,
                                    'discount_type': self.so_id.discount_type,
                                    'discount_method': self.so_id.discount_method,
                                    'discount_amount': self.so_id.discount_amount,
                                    'multi_discount': self.so_id.multi_discount
                                }
                            line_vals = {
                                'product_id': order_line.product_id.id,
                                'name': order_line.product_id.name,
                                'status': 'draft',
                                'product_uom': order_line.product_uom.id,
                                'product_qty': order_line.product_qty,
                                'price_unit': order_line.price_unit,
                                'picking_type_id': order_line.order_id.warehouse_id.in_type_id.id,
                                'destination_warehouse_id': order_line.line_warehouse_id_new.id,
                                'analytic_tag_ids': order_line.account_tag_ids.ids,
                                'taxes_id': [(6, 0, order_line.tax_id.ids)],
                                'discount_method': order_line.discount_method,
                                'multi_discount': order_line.multi_discount,
                                'discount_amount': order_line.discount_amount,
                                'discounted_value': order_line.discounted_value
                            }
                            po_line.append((0, 0, line_vals))
                        if po_line:
                            # vals['order_line'] = po_line
                            purchase_order_id = self.env['purchase.order'].with_context(context).create(vals)
                            purchase_order_id.write({'order_line': po_line})
                            purchase_order_id._onchange_partner_invoice_id()
                            if self.sh_create_po == 'po':
                                purchase_order_id.selected_order = True
                                purchase_order_id.button_confirm()
                            else:
                                purchase_order_id.selected_order = False

                            order_ids.append(purchase_order_id.id)

                return {
                    'name': _("Purchase Orders/RFQ's"),
                    'type': 'ir.actions.act_window',
                    'res_model': 'purchase.order',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'domain': [('id', 'in', order_ids)],
                    'target': 'current',
                    'context': context,
                }
            else:
                if self.env['ir.config_parameter'].sudo().get_param('is_good_services_order') == 'True': 
                    # GOODS ORDER 
                    context = clean_context.copy()
                    context['goods_order'] = True
                    vals = {}
                    po_line = []
                    for order_line in purchase_order_line.filtered(lambda l:l.product_id.type not in ('service','asset')):
                        if not vals:
                            vals = {
                                'requested_by':self.env.uid,
                                'origin':self.so_id.display_name,
                                'destination_warehouse':self.so_id.warehouse_id.id,
                                'customer_partner_id':self.so_id.partner_id.id,
                                'customer_location_partner_id':self.so_id.partner_shipping_id.id,
                                'branch_id': order_line.order_id.branch_id.id,
                                'analytic_account_group_ids': [(6, 0, self.so_id.account_tag_ids.ids)],
                                'so_id':self.so_id.id,
                                'is_dropship':self.is_dropship,
                                'is_goods_orders': True,
                                'is_single_delivery_destination':self.is_dropship or self.so_id.is_single_warehouse
                            }
                        line_vals = {
                            'product_id': order_line.product_id.id,
                            'name': order_line.product_id.name,
                            'product_uom_id': order_line.product_uom.id,
                            'product_qty': order_line.product_qty,
                            'estimated_cost': order_line.price_unit,
                            'dest_loc_id': self.so_id.warehouse_id.id,
                            'analytic_account_group_ids': [(6, 0, order_line.account_tag_ids.ids)],
                            'is_goods_orders':True,
                        }
                        po_line.append((0, 0, line_vals))
                    if po_line:
                        vals['line_ids'] = po_line
                        purchase_order_id = self.env['purchase.request'].with_context(context).create(vals)
                        order_ids.append(purchase_order_id.id)

                    # SERVICES ORDER 
                    context = clean_context.copy()
                    context['services_good'] = True
                    vals = {}
                    po_line = []
                    for order_line in purchase_order_line.filtered(lambda l:l.product_id.type == 'service'):
                        if not vals:
                            vals = {
                                'requested_by':self.env.uid,
                                'origin':self.so_id.display_name,
                                'destination_warehouse':self.so_id.warehouse_id.id,
                                'customer_partner_id':self.so_id.partner_id.id,
                                'customer_location_partner_id':self.so_id.partner_shipping_id.id,
                                'branch_id': order_line.order_id.branch_id.id,
                                'analytic_account_group_ids': [(6, 0, self.so_id.account_tag_ids.ids)],
                                'so_id':self.so_id.id,
                                'is_dropship':self.is_dropship,
                                'is_services_orders': True,
                                'is_single_delivery_destination':self.is_dropship or self.so_id.is_single_warehouse
                            }
                        line_vals = {
                            'product_id': order_line.product_id.id,
                            'name': order_line.product_id.name,
                            'product_uom_id': order_line.product_uom.id,
                            'product_qty': order_line.product_qty,
                            'estimated_cost': order_line.price_unit,
                            'dest_loc_id': self.so_id.warehouse_id.id,
                            'analytic_account_group_ids': [(6, 0, order_line.account_tag_ids.ids)],
                            'is_services_orders':True,
                        }
                        po_line.append((0, 0, line_vals))
                    if po_line:
                        vals['line_ids'] = po_line
                        purchase_order_id = self.env['purchase.request'].with_context(context).create(vals)
                        order_ids.append(purchase_order_id.id)

                    
                    # ASSETS ORDER 
                    context = clean_context.copy()
                    context['assets_orders'] = True
                    vals = {}
                    po_line = []
                    for order_line in purchase_order_line.filtered(lambda l:l.product_id.type == 'asset'):
                        if not vals:
                            vals = {
                                'requested_by':self.env.uid,
                                'origin':self.so_id.display_name,
                                'destination_warehouse':self.so_id.warehouse_id.id,
                                'customer_partner_id':self.so_id.partner_id.id,
                                'customer_location_partner_id':self.so_id.partner_shipping_id.id,
                                'branch_id': order_line.order_id.branch_id.id,
                                'analytic_account_group_ids': [(6, 0, self.so_id.account_tag_ids.ids)],
                                'so_id':self.so_id.id,
                                'is_dropship':self.is_dropship,
                                'is_assets_orders': True,
                                'is_single_delivery_destination':self.is_dropship or self.so_id.is_single_warehouse
                            }
                        line_vals = {
                            'product_id': order_line.product_id.id,
                            'name': order_line.product_id.name,
                            'product_uom_id': order_line.product_uom.id,
                            'product_qty': order_line.product_qty,
                            'estimated_cost': order_line.price_unit,
                            'dest_loc_id': self.so_id.warehouse_id.id,
                            'analytic_account_group_ids': [(6, 0, order_line.account_tag_ids.ids)],
                            'is_assets_orders':True,
                        }
                        po_line.append((0, 0, line_vals))
                    if po_line:
                        vals['line_ids'] = po_line
                        purchase_order_id = self.env['purchase.request'].with_context(context).create(vals)
                        order_ids.append(purchase_order_id.id)

                else:
                    # ALL ORDER 
                    vals = {}
                    po_line = []
                    for order_line in purchase_order_line:
                        if not vals:
                            vals = {
                                'requested_by':self.env.uid,
                                'origin':self.so_id.display_name,
                                'destination_warehouse':self.so_id.warehouse_id.id,
                                'customer_partner_id':self.so_id.partner_id.id,
                                'customer_location_partner_id':self.so_id.partner_shipping_id.id,
                                'branch_id': order_line.order_id.branch_id.id,
                                'analytic_account_group_ids': [(6, 0, self.so_id.account_tag_ids.ids)],
                                'so_id':self.so_id.id,
                                'is_dropship':self.is_dropship,
                                'is_assets_orders': True,
                                'is_single_delivery_destination':self.is_dropship or self.so_id.is_single_warehouse
                            }
                        line_vals = {
                            'product_id': order_line.product_id.id,
                            'name': order_line.product_id.name,
                            'product_uom_id': order_line.product_uom.id,
                            'product_qty': order_line.product_qty,
                            'estimated_cost': order_line.price_unit,
                            'dest_loc_id': self.so_id.warehouse_id.id,
                            'analytic_account_group_ids': [(6, 0, order_line.account_tag_ids.ids)],
                            'is_assets_orders':True,
                        }
                        po_line.append((0, 0, line_vals))
                    if po_line:
                        vals['line_ids'] = po_line
                        purchase_order_id = self.env['purchase.request'].with_context(context).create(vals)
                        order_ids.append(purchase_order_id.id)

                return {
                    'name': _("Purchase Request's"),
                    'type': 'ir.actions.act_window',
                    'res_model': 'purchase.request',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'domain': [('id', 'in', order_ids)],
                    'target': 'current',
                    'context': context,
                }
        