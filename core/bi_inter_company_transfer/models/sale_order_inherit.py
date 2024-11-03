# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.


from itertools import groupby
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError ,Warning
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang
from odoo.tools import html2plaintext
import odoo.addons.decimal_precision as dp

class SaleOrderLineInherit(models.Model):
    _inherit = "sale.order.line"

    @api.depends('move_ids.state', 'move_ids.scrapped', 'move_ids.product_uom_qty', 'move_ids.product_uom')
    def _compute_qty_delivered(self):
        super(SaleOrderLineInherit, self)._compute_qty_delivered()

        for line in self:  # TODO: maybe one day, this should be done in SQL for performance sake
            if line.qty_delivered_method == 'stock_move':
                qty = 0.0
                for move in line.move_ids.filtered(lambda r: r.state == 'done' and not r.scrapped and line.product_id == r.product_id):
                    if move.location_dest_id.usage == "customer":
                        if not move.origin_returned_move_id or (move.origin_returned_move_id and move.to_refund):
                            qty += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom)
                    elif move.location_dest_id.usage != "customer" and move.to_refund:
                        qty -= move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom)
                    else:
                        qty += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom)
                line.qty_delivered = qty    


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    @api.depends('internal_id')
    def _compute_internal(self):
        for internal in self:
            internal_transfer = self.env['inter.transfer.company'].search([('id','=',internal.internal_id.id)])
            if internal_transfer:
                internal.inter_transfer_count = len(internal_transfer)  

    internal_id = fields.Many2one('inter.transfer.company',copy=False)
    inter_transfer_count =  fields.Integer(string= "Internal Transfer" ,compute="_compute_internal", copy=False, default=0, store=True)
    client_order_id = fields.Many2one(comodel_name="purchase.order", string="Purchase Order Inter Transfer")

    def action_view_internal(self):
        action = self.env.ref('bi_inter_company_transfer.stock_inter_company_transfer_action').read()[0]
        domain = [('id', '=', self.internal_id.id)]
        transfer = self.env['inter.transfer.company'].search(domain)
        action['domain'] = [('id', '=', transfer.id)]
        return action


    def action_confirm(self):
        res  = super(SaleOrderInherit, self).action_confirm()
        setting_id = self.env.user.company_id
        invoice = False
        create_picking = False
        internal_id  =  self.env['inter.transfer.company']
        inter_transfer_lines = self.env['inter.transfer.company.line']
        company_partner_id = self.partner_id.related_company_id
        po_available = self.env['purchase.order'].search([('partner_ref','=',self.client_order_ref)])
        if self.env.user.has_group('bi_inter_company_transfer.group_ict_manager_access') and self.env.company.allow_auto_intercompany:
            if company_partner_id.id:
                if setting_id.validate_picking:
                    for picking  in self.picking_ids:
                        for move in picking.move_ids_without_package:
                            move.write({'quantity_done':move.product_uom_qty})
                            if self.internal_id.id == False and self.client_order_ref == False:
                                data = inter_transfer_lines._prepare_internal_from_move_line(move)
                                internal_line = inter_transfer_lines.new(data)
                                inter_transfer_lines += internal_line
                        picking._action_done()
                        if picking.state == 'done':
                            create_picking = True
                else :
                    for picking  in self.picking_ids:
                        for move in picking.move_ids_without_package:
                            if self.internal_id.id == False and self.client_order_ref == False:
                                data = inter_transfer_lines._prepare_internal_from_move_line(move)
                                internal_line = inter_transfer_lines.new(data)
                                inter_transfer_lines += internal_line
                if setting_id.create_invoice:
                    invoice = self._create_invoices()
                if setting_id.validate_invoice:
                    if invoice:
                        invoice_id = self.env['account.move'].browse(invoice.id)
                        invoice_id._post()
                    else:
                        raise Warning(_('Please First give access to Create invoice.'))             
                if self.internal_id.id == False and self.client_order_ref == False:
                    internal_transfer_id = internal_id.create({
                                                            'sale_id':self.id, 
                                                            'invoice_id':[(6,0 , self.invoice_ids.ids)],
                                                            'state':'process',
                                                            'apply_type':'purchase',
                                                            'from_warehouse':self.warehouse_id.id,
                                                            'pricelist_id':self.pricelist_id.id,
                                                            })
                    self.internal_id = internal_transfer_id.id
                    internal_transfer_id.product_lines += inter_transfer_lines
                else:
                    created_id = internal_id.search([('id','=',self.internal_id.id)])
                    if not created_id.from_warehouse.id:
                        created_id.write({
                            'sale_id':self.id or False,
                            'from_warehouse':self.warehouse_id.id,
                            'pricelist_id':self.pricelist_id.id or False,
                            'invoice_id':[(6, 0 , self.invoice_ids.ids)],
                            })
                    else:
                        created_id.write({
                            'sale_id':self.id or False,
                            'pricelist_id':self.pricelist_id.id or False,
                            'invoice_id':[(6, 0 , self.invoice_ids.ids)],
                            })
            if self.client_order_ref == False:
                if company_partner_id.id:
                    if self._context.get('stop_po') == True :
                        pass
                    else :
                        receipt  = self._create_po_from_so(company_partner_id)
        return True

    def _create_po_from_so(self , company):
        company_partner_id = self.partner_id.related_company_id
        current_company_id = self.env.company
        purchase_order = self.env['purchase.order']
        purchase_order_line = self.env['purchase.order.line']
        picking_validate = False
        create_invoice = False
        validate_invoice = False
        bill_id = False
        po_vals = self.sudo().get_po_values(company_partner_id , current_company_id)
        po_id = purchase_order.sudo().create(po_vals)
        for line in self.order_line:
            po_line_vals = self.sudo().get_po_line_data( po_id.id, company_partner_id, line)
            purchase_order_line.sudo().create(po_line_vals)
        if not self.client_order_id:
            self.client_order_id = po_id.id
        po_id.sudo().button_confirm()
        setting_id = self.env.user.company_id
        if setting_id.validate_picking:
            for receipt in po_id.picking_ids:
                for move in receipt.move_ids_without_package:
                    move.write({'quantity_done':move.product_uom_qty})              
                receipt.sudo()._action_done()
                if receipt.state == 'done':
                    picking_validate = True
        if setting_id.create_invoice:
            if setting_id.create_invoice ==True:
                invoice_object = self.env['account.move']
                invoice_line_obj = self.env['account.move.line']
                journal = self.env['account.journal'].sudo().search([('type', '=', 'purchase'),('company_id','=',company.id)], limit=1)
                internal_id  =  self.env['inter.transfer.company']
                inter_transfer_lines = self.env['inter.transfer.company.line']
                ctx = dict(self._context or {})
                ctx.update({
                    'move_type': 'in_invoice',
                    'default_purchase_id': po_id.id,
                    'default_currency_id': po_id.currency_id.id,
                    'default_origin' : po_id.name,
                    'default_reference' : po_id.name,
                    'current_company_id':current_company_id.id,
                    'company_partner_id' : company_partner_id.id
                    })    
                bill_id = invoice_object.with_context(create_bill = True).sudo().with_company(company).create({'partner_id': po_id.partner_id.id,
                                                'currency_id':po_id.currency_id.id,
                                                'company_id':po_id.company_id.id,
                                                'move_type': 'in_invoice',
                                                'journal_id':journal.id,
                                                'purchase_vendor_bill_id' : po_id.id,
                                                'purchase_id':po_id.id,
                                                'ref':po_id.name})


                new_lines = self.env['account.move.line']
                new_lines = []
                for line in po_id.order_line.filtered(lambda l: not l.display_type):
                    new_lines.append((0,0,line._prepare_account_move_line(bill_id)))                      
                bill_id.write({
                    'invoice_line_ids' : new_lines,
                    'purchase_id' : False,
                    'invoice_date' : bill_id.date
                    })   
                bill_id.invoice_payment_term_id = po_id.payment_term_id
                bill_id.invoice_origin = ', '.join(po_id.mapped('name'))
                bill_id.ref = ', '.join(po_id.filtered('partner_ref').mapped('partner_ref')) or bill_id.reference 
        if setting_id.validate_invoice:
            if bill_id:
                bill_id.sudo().with_company(company)._post()
            else:
                raise Warning(_('Please First give access to Create invoice.'))
        
        if self.internal_id.id:
            if po_id.id:
                if not self.internal_id.to_warehouse.id:
                    self.internal_id.update({
                    'purchase_id':po_id.id or False,
                    'currency_id':po_id.currency_id.id or False,
                    'to_warehouse':company_partner_id.intercompany_warehouse_id.id                 
                    })
                else:
                    self.internal_id.update({
                    'purchase_id':po_id.id or False,
                    'currency_id':po_id.currency_id.id or False,
                    })
            if bill_id:
                bill_details = []
                bill_details.append(bill_id.id)
                if len(self.internal_id.invoice_id) > 0:
                    for inv in self.internal_id.invoice_id:
                        bill_details.append(inv.id)
                self.internal_id.update({
                    'invoice_id':[( 6, 0 , bill_details )], 
                    })  
        if not po_id.internal_id.id:
            po_id.internal_id = self.internal_id.id
        return po_id

    def get_po_line_data(self, po_id,company ,line):

        fpos = line.order_id.fiscal_position_id or line.order_id.partner_id.property_account_position_id
        taxes = line.product_id.taxes_id.filtered(lambda r: not line.company_id or r.company_id == company)
        tax_ids = fpos.map_tax(taxes, line.product_id, line.order_id.partner_shipping_id) if fpos else taxes        
        price = line.price_unit - (line.price_unit * (line.discount / 100))
        quantity = line.product_uom._compute_quantity(line.product_uom_qty, line.product_id.uom_po_id) or line.product_uom_qty
        price = line.product_uom._compute_price(price, line.product_id.uom_po_id) or price
        return {
            'name': line.name,
            'date_planned': line.order_id.expected_date,
            'taxes_id': [(6, 0, tax_ids.ids)],
            'order_id': po_id,
            'product_qty': quantity,
            'product_id': line.product_id and line.product_id.id or False,
            'product_uom': line.product_id and line.product_id.uom_po_id.id or line.product_uom.id,
            'price_unit': price or 0.0,
        }       

    def get_po_values(self , company_partner_id , current_company_id):
        warehouse_id = self.env['stock.warehouse'].search([('company_id','=',company_partner_id.id)],limit=1)
        current_cmp_warehouse = self.env['stock.warehouse'].search([('company_id','=',current_company_id.id)], limit =1 )
        po_name = self.env['ir.sequence'].sudo().next_by_code('purchase.order')
        if company_partner_id :
            if not company_partner_id.intercompany_warehouse_id :
                raise Warning(_('Please Select Intercompany Warehouse On  %s.')%company_partner_id.name) 
        other_cmp_warehouse = company_partner_id.intercompany_warehouse_id 
        picking_type_id = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'), ('warehouse_id', '=', other_cmp_warehouse.id) 
        ], limit=1)
        if self.internal_id.id:
            if self.internal_id.currency_id.id:
                currency_id = self.internal_id.currency_id.id
            else:
                currency_id = self.currency_id.id
        else:
            currency_id = self.currency_id.id

        partner_id = self.env['res.partner'].sudo().search([
            ('related_company_id', '=', current_company_id.id),
            ('company_id', '=', company_partner_id.id)
        ], limit=1)
        res = {
            'name': po_name,
            'origin': self.name,
            'fiscal_position_id': partner_id.property_account_position_id.id,
            'payment_term_id': partner_id.property_supplier_payment_term_id.id,
            'partner_ref': self.name,
            'currency_id': currency_id,
            'user_id':self.env.uid,
            'partner_id': partner_id.id,
            'internal_id' :self.internal_id.id,
            'date_order': self.date_order,
            'company_id': company_partner_id.id,
        }
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: