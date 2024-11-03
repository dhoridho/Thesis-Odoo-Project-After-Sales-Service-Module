# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from itertools import groupby
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, SUPERUSER_ID ,_
from odoo.exceptions import UserError, ValidationError , Warning
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang
from odoo.tools import html2plaintext
import odoo.addons.decimal_precision as dp
import time

class PurchaseOrderInherit(models.Model):
    _inherit = 'purchase.order'

    @api.depends('internal_id')
    def _compute_internal(self):
        for internal in self:
            internal_transfer = self.env['inter.transfer.company'].search([('id','=',internal.internal_id.id)])
            if internal_transfer:
                internal.inter_transfer_count = len(internal_transfer)  

    internal_id = fields.Many2one('inter.transfer.company',copy=False)
    inter_transfer_count =  fields.Integer(string= "Internal Transfer" ,compute="_compute_internal", copy=False, default=0, store=True)
    client_order_id = fields.Many2one(comodel_name="sale.order", string="Sale Order Inter Transfer")

    def action_view_internal(self):
        action = self.env.ref('bi_inter_company_transfer.stock_inter_company_transfer_action').read()[0]
        domain = [('id', '=', self.internal_id.id)]
        transfer = self.env['inter.transfer.company'].search(domain)
        action['domain'] = [('id', '=', transfer.id)]
        return action

    def button_confirm(self):
        res  = super(PurchaseOrderInherit, self).button_confirm()
        company_partner_id = self.partner_id.related_company_id
        so_available = self.env['sale.order'].search([('client_order_id','=',self.id)])
        setting_id = self.env.company
        invoice_object = self.env['account.move']
        invoice_line_obj = self.env['account.move.line']
        journal = self.env['account.journal'].sudo().search([('type', '=', 'purchase'),('company_id','=',self.env.company.id)], limit=1)
        internal_id  =  self.env['inter.transfer.company']
        inter_transfer_lines = self.env['inter.transfer.company.line']
        inter_lines = []
        picking_access = False
        create_invoice = False
        validate_invoice = False
        bill_id =  False
        if self.env.user.has_group('bi_inter_company_transfer.group_ict_manager_access') and self.env.company.allow_auto_intercompany:
            if company_partner_id.id:
                if not so_available.id:
                    if setting_id.validate_picking:
                        for receipt in self.picking_ids:           
                            for move in receipt.move_ids_without_package:
                                move.write({'quantity_done':move.product_uom_qty}) 
                                if self.internal_id.id == False and self.partner_ref == False:
                                    data = inter_transfer_lines.create({
                                                                        'product_id' : move.product_id.id,
                                                                        'quantity' : move.product_uom_qty,
                                                                        'price_unit' : move.product_id.lst_price
                                                                        })      
                                    inter_lines.append(data)                       
                            receipt._action_done()
                            if receipt.state == 'done':
                                picking_access = True
                    else :
                        for receipt in self.picking_ids:           
                            for move in receipt.move_ids_without_package:
                                if self.internal_id.id == False and self.partner_ref == False:
                                    data = inter_transfer_lines.create({
                                                                        'product_id' : move.product_id.id,
                                                                        'quantity' : move.product_uom_qty,
                                                                        'price_unit' : move.product_id.lst_price
                                                                        })          
                                    inter_lines.append(data)                                         
                    if setting_id.create_invoice:
                        if setting_id.create_invoice:
                            ctx = dict(self._context or {})
                            ctx.update({
                                'move_type': 'in_invoice',
                                'default_purchase_id': self.id,
                                'default_currency_id': self.currency_id.id,
                                'default_invoice_origin' : self.name,
                                'default_ref' : self.name,
                                })
                            bill_id = invoice_object.with_context(ctx).create({'partner_id': self.partner_id.id,
                                                        'currency_id':self.currency_id.id,
                                                        'company_id':self.company_id.id,
                                                        'move_type': 'in_invoice',
                                                        'journal_id':journal.id,
                                                        'purchase_vendor_bill_id' : self.id,
                                                        'purchase_id':self.id,
                                                        'ref':self.name})
                            new_lines = self.env['account.move.line']
                            new_lines = []
                            for line in self.order_line.filtered(lambda l: not l.display_type):
                                new_lines.append((0,0,line._prepare_account_move_line(bill_id)))                      
                            bill_id.write({
                                'invoice_line_ids' : new_lines,
                                'purchase_id' : False,
                                'invoice_date' : bill_id.date
                                })   
                            bill_id.invoice_payment_term_id = self.payment_term_id
                            bill_id.invoice_origin = ', '.join(self.mapped('name'))
                            bill_id.ref = ', '.join(self.filtered('partner_ref').mapped('partner_ref')) or bill_id.ref
                    if setting_id.validate_invoice:
                        if bill_id:
                            bill_id._post()  
                        else:
                            raise Warning(_('Please First give access to Create Bill.'))
                    if self.internal_id.id == False and self.partner_ref == False:
                        if bill_id :
                            internal_transfer_id = internal_id.create({
                                                                    'purchase_id':self.id,
                                                                    'state':'process',
                                                                    'apply_type':'sale',
                                                                    'currency_id':self.currency_id.id,
                                                                    'invoice_id':[(6,0 , bill_id.ids )],
                                                                    'to_warehouse':self.picking_type_id.warehouse_id.id})
                            self.internal_id = internal_transfer_id.id
                            for i in inter_lines:
                                i.update({
                                    'internal_id' : self.internal_id.id
                                    })
                        else : 
                            internal_transfer_id = internal_id.create({
                                                                    'purchase_id':self.id,
                                                                    'state':'process',
                                                                    'apply_type':'sale',
                                                                    'currency_id':self.currency_id.id,
                                                                    'to_warehouse':self.picking_type_id.warehouse_id.id})
                            self.internal_id = internal_transfer_id.id
                            for i in inter_lines:
                                i.update({
                                    'internal_id' : self.internal_id.id
                                    })
                    else:
                        created_id = internal_id.search([('id','=',self.internal_id.id)])
                        created_id.write({
                            'purchase_id':self.id,
                            'invoice_id' :[(6 , 0 , bill_id.ids)]
                            })
                    if self.internal_id.id:
                        self.internal_id = self.internal_id.id
                    
            if not so_available.id:
                if company_partner_id.id:
                    if self._context.get('stop_so') == True :
                        pass
                    else :
                        receipt  = self._create_so_from_po(company_partner_id)
        
        return True


    def _create_so_from_po(self , company):
        company_partner_id = self.partner_id.related_company_id
        current_company_id = self.env.company
        sale_order = self.env['sale.order']
        picking_validate = False
        invoice = False
        setting_id = self.env.company
        sale_order_line = self.env['sale.order.line']
        allowed_company_ids = [company_partner_id.id , current_company_id.id]
        so_vals = self.sudo().get_so_values(self.name , company_partner_id , current_company_id)
        so_id = sale_order.with_context(allowed_company_ids=allowed_company_ids).sudo().create(so_vals)
        for line in self.order_line.sudo():
            so_line_vals = self.sudo().get_so_line_data(company_partner_id , so_id.id , line)
            sale_order_line.with_context(allowed_company_ids=allowed_company_ids).sudo().create(so_line_vals)
        if so_id.client_order_id:
            so_id.client_order_id = self.id
        ctx = dict(self._context or {})
        ctx.update({
            'company_partner_id':company_partner_id.id,
            'current_company_id':current_company_id.id
            })
        so_id.with_context(allowed_company_ids=allowed_company_ids).action_confirm()
        
        if setting_id.validate_picking:
            for picking  in so_id.picking_ids:
                for move in picking.move_ids_without_package:
                    move.write({'quantity_done':move.product_uom_qty,
                                'product_uom_qty' : move.product_uom_qty})
                picking._action_done()
                if picking.state == 'done':
                    picking_validate = True
        if setting_id.create_invoice:
            invoice = so_id.order_line.invoice_lines.move_id.filtered(lambda r: r.move_type in ('out_invoice', 'out_refund'))
            if not invoice:
                invoice = so_id.sudo()._create_invoices()

        if setting_id.validate_invoice:
            if invoice:
                if invoice.state != 'posted':
                    invoice_id = self.env['account.move'].browse(invoice.id)
                    invoice_id.sudo()._post()
                else:
                    invoice_id = invoice
            else:
                raise Warning(_('Please First give access to Create invoice.'))                             
        if self.internal_id.id:
            if setting_id.validate_invoice:
                bill_details = []
                bill_details.append(invoice_id.id)
                if len(self.internal_id.invoice_id) > 0:
                    for inv in self.internal_id.invoice_id:
                        bill_details.append(inv.id)
            if not self.internal_id.to_warehouse.id:
                self.internal_id.update({
                    'sale_id':so_id.id,
                    'pricelist_id':so_id.pricelist_id.id,
                    'from_warehouse':so_id.warehouse_id.id,
                    'to_warehouse':current_company_id.intercompany_warehouse_id.id
                    })
            else:
                self.internal_id.update({
                    'sale_id':so_id.id,
                    'pricelist_id':so_id.pricelist_id.id,
                    'from_warehouse':so_id.warehouse_id.id,
                    })
                
            so_id.internal_id = self.internal_id.id
        return so_id    


    @api.model
    def get_so_line_data(self, company, sale_id,line):
        fpos = line.order_id.fiscal_position_id or line.order_id.partner_id.property_account_position_id
        taxes = line.product_id.taxes_id.filtered(lambda r: not line.company_id or r.company_id == company)
        tax_ids = fpos.map_tax(taxes, line.product_id, line.order_id.partner_shipping_id) if fpos else taxes            
        quantity = line.product_uom._compute_quantity(line.product_qty, line.product_id.uom_id)
        
        price = line.price_unit or 0.0
        price = line.product_uom._compute_price(price, line.product_id.uom_id)
        return {
            'name': line.name,
            'customer_lead': line.product_id and line.product_id.sale_delay or 0.0,
            'tax_id': [(6, 0,tax_ids.ids)],
            'order_id': sale_id,
            'product_uom_qty': quantity,
            'product_id': line.product_id and line.product_id.id or False,
            'product_uom': line.product_id and line.product_id.uom_id.id or line.product_uom.id,
            'price_unit': price,
            'company_id' : company.id
        }

    def get_so_values(self ,name , company_partner_id , current_company_id):
        if company_partner_id :
            if not company_partner_id.intercompany_warehouse_id :
                raise Warning(_('Please Select Intercompany Warehouse On  %s.')%company_partner_id.name) 
        so_name = self.env['ir.sequence'].sudo().next_by_code('sale.order') or '/'
        if self.internal_id.id:
            if self.internal_id.pricelist_id.id:
                pricelist_id = self.internal_id.pricelist_id.id
            else:
                pricelist_id = current_company_id.intercompany_warehouse_id.partner_id.property_product_pricelist.id
        else:
            pricelist_id = current_company_id.intercompany_warehouse_id.partner_id.property_product_pricelist.id
        return {
            'name': so_name,
            'partner_invoice_id': current_company_id.intercompany_warehouse_id.partner_id.id,
            'date_order': self.date_order,
            'fiscal_position_id': current_company_id.intercompany_warehouse_id.partner_id.property_account_position_id.id,
            'payment_term_id': current_company_id.intercompany_warehouse_id.partner_id.property_payment_term_id.id,
            'user_id': False,
            'company_id': company_partner_id.id,
            'warehouse_id': company_partner_id.intercompany_warehouse_id.id,
            'client_order_ref': name,
            'partner_id': current_company_id.intercompany_warehouse_id.partner_id.id,
            'pricelist_id': pricelist_id,
            'internal_id' :self.internal_id.id,
            'partner_shipping_id': current_company_id.intercompany_warehouse_id.partner_id.id
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: