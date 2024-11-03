# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.


from itertools import groupby
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang
from odoo.tools import html2plaintext
import odoo.addons.decimal_precision as dp

class InterTransferCompany(models.Model):
    _name = 'inter.transfer.company'
    _description = 'Inter Transfer Company'
    _order = 'create_date desc, id desc'

    @api.depends('invoice_id')
    def _get_invoiced(self):
        for internal in self:
            internal_transfer = self.env['account.move'].search([('id','in',internal.invoice_id.ids),('move_type', '=','out_invoice')])
            if internal_transfer:
                internal.invoice_count = len(internal_transfer)

    @api.depends('invoice_id')
    def _get_bill(self):

        for internal in self:

            internal_transfer = self.env['account.move'].search([('id','in',internal.invoice_id.ids),('move_type', '=','in_invoice')])
            
            if internal_transfer:
                internal.bill_count = len(internal_transfer)

    @api.depends('return_id')
    def _get_returned(self):
        for internal in self:
            internal_transfer = self.env['return.inter.transfer.company'].search([('id','=',self.return_id.id)])
            if internal_transfer:
                internal.return_count = len(internal_transfer)  

    @api.depends('sale_id')
    def _compute_sale_internal(self):
        for internal in self:
            internal_transfer = self.env['sale.order'].search([('id','=',self.sale_id.id)])
            if internal_transfer:
                internal.sale_count = len(internal_transfer)    

    @api.depends('purchase_id')
    def _compute_purchase_internal(self):
        for internal in self:
            internal_transfer = self.env['purchase.order'].search([('id','=',self.purchase_id.id)])
            if self.purchase_id:
                internal.purchase_count = len(self.purchase_id)

    def action_view_sale_internal(self):
        action = self.env.ref('sale.action_orders').read()[0]
        domain = [('id', '=', self.sale_id.id)]
        transfer = self.env['sale.order'].search(domain)
        action['domain'] = [('id', '=', transfer.id)]
        return action

    def action_view_return_internal(self):
        action = self.env.ref('bi_inter_company_transfer.return_inter_company_transfer_action').read()[0]
        domain = [('id', '=', self.return_id.id)]
        transfer = self.env['return.inter.transfer.company'].search(domain)
        action['domain'] = [('id', '=', transfer.id)]
        return action

    def action_view_invoice_internal(self):
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('account.action_move_out_invoice_type')
        list_view_id = imd.xmlid_to_res_id('account.view_invoice_tree')
        form_view_id = imd.xmlid_to_res_id('account.view_move_form')
        result = {      
            
                        'name': action.name,
                        'help': action.help,
                        'type': action.type,
                        'views': [ (list_view_id ,'tree'),(form_view_id,'form')],
                        'target': action.target,
                        'context': action.context,
                        'res_model': action.res_model,
                    }
        for invoice in self.invoice_id:
            if invoice.move_type == 'out_invoice':
                result['domain'] = "[('id','in',%s)]" % invoice.ids
                return result

    def action_view_invoice_internal_bill(self):
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('account.action_move_in_invoice_type')
        list_view_id = imd.xmlid_to_res_id('account.view_invoice_tree')
        form_view_id = imd.xmlid_to_res_id('account.view_move_form')
        result = {      
            
                        'name': action.name,
                        'help': action.help,
                        'type': action.type,
                        'views': [ (list_view_id ,'tree'),(form_view_id,'form')],
                        'target': action.target,
                        'context': action.context,
                        'res_model': action.res_model,
                    }
        for invoice in self.invoice_id:
            if invoice.move_type == 'in_invoice':
                result['domain'] = "[('id','in',%s)]" % invoice.ids
                return result

    def action_view_purchase_internal(self):
        action = self.env.ref('purchase.purchase_form_action').read()[0]
        domain = [('id', '=', self.purchase_id.id)]
        transfer = self.env['purchase.order'].search(domain)
        action['domain'] = [('id', '=', transfer.id)]
        return action               

    sale_id = fields.Many2one("sale.order",string="Sale Order", copy=False)
    sale_count = fields.Integer('Sale Count',compute="_compute_sale_internal", copy=False, default=0, store=True)
    invoice_count = fields.Integer(string='Invoice Count', compute="_get_invoiced", copy=False, default=0, store=True)
    bill_count = fields.Integer(string='Bill Count', compute="_get_bill", copy=False, default=0, store=True)
    invoice_id = fields.Many2many("account.move", string='Invoices', copy=False)
    purchase_id = fields.Many2one("purchase.order",string="Purchase Order", copy=False)
    purchase_count = fields.Integer('Purchase Count',compute="_compute_purchase_internal", copy=False, default=0, store=True)
    return_id = fields.Many2one("return.inter.transfer.company", string='return', copy=False)
    return_count = fields.Integer(string='Return Count' ,compute="_get_returned", copy=False, default=0, store=True)
    name = fields.Char("Name", readonly=True, copy=False )
    state= fields.Selection([('draft','Draft'),('process','Process'),('return','Return')],string="state",default='draft', readonly=True)
    from_warehouse = fields.Many2one('stock.warehouse' ,string="From Warehouse" , domain = lambda self : self.from_get_domain())
    currency_id =  fields.Many2one('res.currency',string="Currency")
    to_warehouse = fields.Many2one('stock.warehouse',string="To Warehouse" , domain = lambda self : self.to_get_domain())
    pricelist_id = fields.Many2one('product.pricelist',string="Pricelist")
    apply_type = fields.Selection([('sale', 'Sale Order'), ('purchase', 'Purchase Order'),
          ('sale_purchase', 'Sale and Purchase Order')],default="sale_purchase",string="Apply Type")
    product_lines = fields.One2many('inter.transfer.company.line','internal_id',string="lines")

    def to_get_domain(self):
        return [('company_id','!=',self.env.company.id)]

    def from_get_domain(self):
        return [('company_id','=',self.env.company.id)]     

    @api.model
    def create(self,vals):
       
        ict_name = self.env['ir.sequence'].next_by_code('inter.transfer.company')
        vals['name'] =ict_name
        res  = super(InterTransferCompany, self).create(vals)
        return res

    @api.onchange('from_warehouse')
    def change_details(self):
        res = {}
        if not self.from_warehouse:
            return res
        from_partner = self.from_warehouse.company_id.partner_id
        self.currency_id = from_partner.currency_id.id
        self.pricelist_id = from_partner.property_product_pricelist.id


    def check_tansfer_details(self):
        if len(self.product_lines) == 0:
            raise ValidationError(_('Please Select any one line for Inter Company Transfer.'))

        if self.apply_type == 'sale':
            self.with_context(stop_po = True).createsaleorder()
            
        if self.apply_type == 'purchase':
            self.with_context(stop_so = True).createpurchaseorder()
            
        if self.apply_type == 'sale_purchase':
            self.createsaleorder()

    def action_cancel(self):
        self.update({'state':'cancel'})


    def createsaleorder(self):
        sale_order = self.env['sale.order'].create({
                'partner_id':self.to_warehouse.company_id.partner_id.id,
                'user_id':self.env.uid,
                'internal_id' :self.id,
                'pricelist_id':self.pricelist_id.id,
                'warehouse_id':self.from_warehouse.id,
            })
        for line in self.product_lines:
            company_id = self.env['res.company'].search([('partner_id','=',self.from_warehouse.company_id.partner_id.id)])
            partner_c_id = self.env['res.company'].search([('partner_id','=',self.to_warehouse.company_id.partner_id.id)])
            fpos = sale_order.fiscal_position_id or sale_order.partner_id.property_account_position_id
            taxes = line.product_id.taxes_id.filtered(lambda r: r.company_id == self.env.user.company_id)
            tax_ids = fpos.map_tax(taxes, line.product_id, line.order_id.partner_shipping_id) if fpos else taxes
            sale_order_line_vals = {
                                'product_id': line.product_id.id,
                                'name': line.product_id.name,
                                'product_uom_qty': line.quantity,
                                'product_uom': line.product_id.uom_id.id,
                                'tax_id':[(6, 0, tax_ids.ids)],
                                'price_unit' : line.price_unit,
                                'order_id': sale_order.id
                            }
            sale_order_line_id = self.env['sale.order.line'].create(sale_order_line_vals)
        
        sale_order.action_confirm()
        
        return self.write({'state':'process'})

    def createpurchaseorder(self):
        
        purchase_order = self.env['purchase.order'].create({
                'partner_id':self.to_warehouse.company_id.partner_id.id,
                'user_id':self.env.uid,
                'internal_id' :self.id,
                'currency_id': self.currency_id.id,
            })
        
        for line in self.product_lines:
            company_id = self.env['res.company'].search([('partner_id','=',self.from_warehouse.company_id.partner_id.id)])
            partner_c_id = self.env['res.company'].search([('partner_id','=',self.to_warehouse.company_id.partner_id.id)])
            fpos = purchase_order.fiscal_position_id or purchase_order.partner_id.property_account_position_id
            taxes = line.product_id.taxes_id.filtered(lambda r: r.company_id == self.env.user.company_id)
            tax_ids = fpos.map_tax(taxes, line.product_id, line.order_id.partner_shipping_id) if fpos else taxes
            purchase_order_line_vals = {
                                'product_id': line.product_id.id,
                                'name': line.product_id.name,
                                'product_qty': line.quantity,
                                'date_planned': datetime.now(),
                                'taxes_id':[(6, 0,tax_ids.ids)],
                                'product_uom': line.product_id.uom_id.id,
                                'price_unit' : line.price_unit,
                                'order_id': purchase_order.id
                            }
            purchase_order_line_id = self.env['purchase.order.line'].create(purchase_order_line_vals)
        purchase_order.button_confirm()
        return self.write({'state':'process'})      

    def action_view_return_form(self):
        '''
        This function returns an action that display existing vendor bills of given purchase order ids.
        When only one found, show the vendor bill immediately.
        '''
        # self.write({'state' : 'return'})
        action = self.env.ref('bi_inter_company_transfer.action_return_form_template')
        result = action.read()[0]

        # override the context to get rid of the default filtering
        
        value = []
        for i in self.product_lines:
            vals = ({
            'product_id' : i.product_id.id,
            'quantity' : i.quantity,
            'price_unit' : i.price_unit
            })
            value.append(vals)
        result['context'] = {
            'default_internal_id': self.id,
            'default_from_warehouse': self.from_warehouse.id,
            'default_to_warehouse': self.to_warehouse.id,
            'default_pricelist_id':self.pricelist_id.id,
            'default_currency_id':self.currency_id.id,
            'default_sale_id':self.sale_id.id,
            'default_purchase_id':self.purchase_id.id,
            'default_product_lines':value
        }

        return result
        

class InterTransferCompanyLines(models.Model):
    _name = 'inter.transfer.company.line'
    _description = 'Inter Tranfer Company Line'
    
    internal_id = fields.Many2one('inter.transfer.company')
    product_id = fields.Many2one('product.product' , required = True)
    quantity = fields.Integer('Quantity' , default= 1 , required = True)
    price_unit = fields.Float('Price' , related = "product_id.lst_price")

    def _prepare_internal_from_move_line(self , move):
        return({
            'product_id' : move.product_id.id,
            'quantity' : move.product_uom_qty,
            'price_unit' : move.product_id.lst_price
            })

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: