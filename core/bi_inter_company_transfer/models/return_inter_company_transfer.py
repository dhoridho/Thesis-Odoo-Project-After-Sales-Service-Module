# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.


from itertools import groupby
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError , Warning
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang
from odoo.tools import html2plaintext
import odoo.addons.decimal_precision as dp


class ReturnPickingLine(models.Model):
    _name = "stock.return.picking.inter.company"
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string="Product",  domain="[('id', '=', product_id)]")
    quantity = fields.Float("Quantity", digits='Product Unit of Measure')
    uom_id = fields.Many2one('product.uom', string='Unit of Measure', related='move_id.product_uom')
    wizard_id = fields.Many2one('return.inter.transfer.company', string="Wizard")
    move_id = fields.Many2one('stock.move', "Move")

class ReturnInterTransferCompany(models.Model):
    _name = 'return.inter.transfer.company'
    _description = 'Return Inter Transfer Company'
    _order = 'create_date desc, id desc'

    @api.depends('internal_id')
    def _get_internal(self):
        for internal in self:
            internal_transfer = self.env['inter.transfer.company'].search([('id','=',self.internal_id.id)])
            if internal_transfer:
                internal.internal_count = len(internal_transfer)

    @api.depends('invoice_id')
    def _get_invoiced(self):
        for internal in self:
            internal_transfer = self.env['account.move'].search([('id','in',self.invoice_id.ids),('move_type', 'in', ['out_refund'])])
            if internal_transfer:
                internal.invoice_count = len(internal_transfer)

    @api.depends('invoice_id')
    def _get_bill(self):

        for internal in self:
            internal_transfer = self.env['account.move'].search([('id','in',internal.invoice_id.ids),('move_type', '=','in_refund')])
            if internal_transfer:
                internal.bill_count = len(internal_transfer)
                
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
            if internal_transfer:
                internal.purchase_count = len(internal_transfer)    

    sale_id = fields.Many2one("sale.order",string="Sale Order")
    sale_count = fields.Integer('Sale Count',compute="_compute_sale_internal", copy=False, default=0, store=True)
    invoice_count = fields.Integer(string='Invoice Count', compute="_get_invoiced", copy=False, default=0, store=True)
    bill_count = fields.Integer(string='Bill Count', compute="_get_bill", copy=False, default=0, store=True)
    invoice_id = fields.Many2many("account.move", string='Invoices', copy=False)
    purchase_id = fields.Many2one("purchase.order",string="Purchase Order")
    purchase_count = fields.Integer('Purchase Count',compute="_compute_purchase_internal", copy=False, default=0, store=True)
    internal_id= fields.Many2one("inter.transfer.company", string='return' , copy=False)
    internal_count = fields.Integer(string='Internal Count' ,compute="_get_internal", copy=False, default=0, store=True)
    name = fields.Char("Name", readonly=True, copy=False )
    state= fields.Selection([('draft','Draft'),('process','Process'),('return','Return')],string="state",default='draft', readonly=True)
    from_warehouse = fields.Many2one('stock.warehouse' ,string="From warehouse" , required=True)
    currency_id =  fields.Many2one('res.currency',string="Currency")
    to_warehouse = fields.Many2one('stock.warehouse',string="To warehouse",required=True)
    pricelist_id = fields.Many2one('product.pricelist',string="Pricelist")
    product_lines = fields.One2many('return.inter.transfer.company.line','return_id',string="lines")
    product_return_moves = fields.One2many('stock.return.picking.inter.company','wizard_id')

    @api.model
    def create(self,vals):
       
        rict_name = self.env['ir.sequence'].next_by_code('return.inter.transfer.company')
        vals['name'] =rict_name
        res  = super(ReturnInterTransferCompany, self).create(vals)
        internal_id = self.env['inter.transfer.company'].search([('id','=',vals['internal_id'])])
        internal_id.write({
            'return_id':res.id,
            'state' : 'return'
            })
        return res

    def action_view_sale_internal(self):
        action = self.env.ref('sale.action_orders').read()[0]
        domain = [('id', '=', self.sale_id.id)]
        transfer = self.env['sale.order'].search(domain)
        action['domain'] = [('id', '=', transfer.id)]
        return action

    def action_view_internal(self):
        action = self.env.ref('bi_inter_company_transfer.stock_inter_company_transfer_action').read()[0]
        domain = [('id', '=', self.internal_id.id)]
        transfer = self.env['inter.transfer.company'].search(domain)
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
        result['domain'] = "[('id','in',%s)]" % self.invoice_id.ids
        return result

    def action_view_invoice_internal_bill(self):
        action = self.env.ref('account.action_vendor_bill_template').read()[0]
        domain = [('id', 'in', self.invoice_id.ids),('move_type', '=', 'in_refund')]
        transfer = self.env['account.move'].search(domain)
        action['domain'] = [('id', 'in', transfer.ids)]
        return action

    def action_view_purchase_internal(self):
        action = self.env.ref('purchase.purchase_form_action').read()[0]
        domain = [('id', '=', self.purchase_id.id)]
        transfer = self.env['purchase.order'].search(domain)
        action['domain'] = [('id', '=', transfer.id)]
        return action

    def _prepare_move_default_values_inter(self, return_line, new_picking, picking):
        vals = {
            'product_id': return_line.product_id.id,
            'product_uom_qty': return_line.quantity,
            'product_uom': return_line.product_id.uom_id.id,
            'picking_id': new_picking.id,
            'state': 'draft',
            'location_id': return_line.move_id.location_dest_id.id,
            'location_dest_id': picking.location_id.id or return_line.move_id.location_id.id,
            'picking_type_id': new_picking.picking_type_id.id,
            'warehouse_id': picking.picking_type_id.warehouse_id.id,
            'origin_returned_move_id': return_line.move_id.id,
            'procure_method': 'make_to_stock',
        }
        return vals

    def CreateInvoiceCreditNote(self):
        inv_obj = self.env['account.move']
        inv_tax_obj = self.env['account.tax']
        inv_line_obj = self.env['account.move.line']
        context = dict(self._context or {})
        xml_id = False

        created_inv = []
        date = False
        description = False
        mode = 'refund'
        for inv in inv_obj.browse(self.internal_id.invoice_id.ids):
            if inv.move_type == 'out_invoice':
                credit_note_wizard = self.env['account.move.reversal'].with_context({'active_ids': [inv.id], 'active_id': inv.id, 'active_model': 'account.move'}).create({
                    'refund_method': 'refund',  
                    'reason': 'reason test create',
                })
                credit_note_wizard.reverse_moves()
                refund = inv.sorted(key=lambda inv: inv.id, reverse=False)[-1]
                created_inv.append(refund.id)
                if mode in ('cancel', 'modify'):
                    movelines = inv.move_id.line_ids
                    to_reconcile_ids = {}
                    to_reconcile_lines = self.env['account.move.line']
                    for line in movelines:
                        if line.account_id.id == inv.account_id.id:
                            to_reconcile_lines += line
                            to_reconcile_ids.setdefault(line.account_id.id, []).append(line.id)
                        if line.reconciled:
                            line.remove_move_reconcile()
                    refund.action_post()
                    for tmpline in refund.move_id.line_ids:
                        if tmpline.account_id.id == inv.account_id.id:
                            to_reconcile_lines += tmpline
                    to_reconcile_lines.filtered(lambda l: l.reconciled == False).reconcile()
                    if mode == 'modify':
                        invoice = inv.read(inv_obj._get_refund_modify_read_fields())
                        invoice = invoice[0]
                        del invoice['id']
                        invoice_lines = inv_line_obj.browse(invoice['invoice_line_ids'])
                        invoice_lines = inv_obj.with_context(mode='modify')._refund_cleanup_lines(invoice_lines)
                        tax_lines = inv_tax_obj.browse(invoice['tax_line_ids'])
                        tax_lines = inv_obj._refund_cleanup_lines(tax_lines)
                        invoice.update({
                            'type': inv.type,
                            'date_invoice': form.date_invoice,
                            'state': 'draft',
                            'number': False,
                            'invoice_line_ids': invoice_lines,
                            'tax_line_ids': tax_lines,
                            'date': date,
                            'origin': inv.origin,
                            'fiscal_position_id': inv.fiscal_position_id.id,
                        })
                        for field in inv_obj._get_refund_common_fields():
                            if inv_obj._fields[field].type == 'many2one':
                                invoice[field] = invoice[field] and invoice[field][0]
                            else:
                                invoice[field] = invoice[field] or False
                        inv_refund = inv_obj.create(invoice)
                        inv_refund.message_post(body=body)
                        if inv_refund.payment_term_id.id:
                            inv_refund._onchange_payment_term_date_invoice()
                        created_inv.append(inv_refund.id)
                bill_details = []
                if len(self.invoice_id)>0:
                    for inv in self.invoice_id:
                        bill_details.append(inv.id)
                bill_details.append(refund.id)
                self.write({
                    'state':'process',
                    'invoice_id':[(6 ,0 ,bill_details)]
                    })
                refund.action_post()
            
    def CreateBillCreditNote(self):
        inv_obj = self.env['account.move']
        inv_tax_obj = self.env['account.tax']
        inv_line_obj = self.env['account.move.line']
        context = dict(self._context or {})
        xml_id = False

        created_inv = []
        date = False
        description = False
        mode = 'refund'
        for inv in inv_obj.browse(self.internal_id.invoice_id.ids):
            if inv.move_type == 'in_invoice':
                credit_note_wizard = self.env['account.move.reversal'].with_context({'active_ids': [inv.id], 'active_id': inv.id, 'active_model': 'account.move'}).create({
                    'refund_method': 'refund',  
                    'reason': 'reason test create',
                })
                credit_note_wizard.reverse_moves()
                refund = inv.sorted(key=lambda inv: inv.id, reverse=False)[-1]
                created_inv.append(refund.id)
                if mode in ('cancel', 'modify'):
                    movelines = inv.move_id.line_ids
                    to_reconcile_ids = {}
                    to_reconcile_lines = self.env['account.move.line']
                    for line in movelines:
                        if line.account_id.id == inv.account_id.id:
                            to_reconcile_lines += line
                            to_reconcile_ids.setdefault(line.account_id.id, []).append(line.id)
                        if line.reconciled:
                            line.remove_move_reconcile()
                    refund.action_post()
                    for tmpline in refund.move_id.line_ids:
                        if tmpline.account_id.id == inv.account_id.id:
                            to_reconcile_lines += tmpline
                    to_reconcile_lines.filtered(lambda l: l.reconciled == False).reconcile()
                    if mode == 'modify':
                        invoice = inv.read(inv_obj._get_refund_modify_read_fields())
                        invoice = invoice[0]
                        del invoice['id']
                        invoice_lines = inv_line_obj.browse(invoice['invoice_line_ids'])
                        invoice_lines = inv_obj.with_context(mode='modify')._refund_cleanup_lines(invoice_lines)
                        tax_lines = inv_tax_obj.browse(invoice['tax_line_ids'])
                        tax_lines = inv_obj._refund_cleanup_lines(tax_lines)
                        invoice.update({
                            'type': inv.type,
                            'date_invoice': form.date_invoice,
                            'state': 'draft',
                            'number': False,
                            'invoice_line_ids': invoice_lines,
                            'tax_line_ids': tax_lines,
                            'date': date,
                            'origin': inv.origin,
                            'fiscal_position_id': inv.fiscal_position_id.id,
                        })
                        for field in inv_obj._get_refund_common_fields():
                            if inv_obj._fields[field].type == 'many2one':
                                invoice[field] = invoice[field] and invoice[field][0]
                            else:
                                invoice[field] = invoice[field] or False
                        inv_refund = inv_obj.create(invoice)
                        inv_refund.message_post(body=body)
                        if inv_refund.payment_term_id.id:
                            inv_refund._onchange_payment_term_date_invoice()
                        created_inv.append(inv_refund.id)
                bill_details = []
                if len(self.invoice_id)>0:
                    for inv in self.invoice_id:
                        bill_details.append(inv.id)
                bill_details.append(refund.id)
                self.write({
                    'state':'process',
                    'invoice_id':[(6 ,0 ,bill_details)]
                    })
                refund.action_post()

    def ReturnPicking(self):

        pickings = self.sale_id.mapped('picking_ids')
        if pickings:
            for picking in pickings:
                if picking.state == 'done':
                    res = {}
                    product_return_moves = []
                    parent_location_id = False
                    location_id = False
                    original_location_id = False
                    res.update({'picking_id': picking.id})
                    for move in picking.move_lines:
                        for product in self.product_lines:
                            if move.product_id == product.product_id:
                                if move.scrapped:
                                    continue
                                if move.move_dest_ids:
                                    move_dest_exists = True

                                product_return_moves.append((0, 0, {'product_id': move.product_id.id, 'quantity': product.quantity, 'move_id': move.id, 'uom_id': move.product_id.uom_id.id}))
                    self.write({'product_return_moves' : product_return_moves})

                    location_id = picking.location_id.id
                    original_location_id = picking.location_id.id
                    parent_location_id = picking.picking_type_id.warehouse_id.view_location_id.id or picking.location_id.location_id.id
                    
                    for return_move in self.product_return_moves.mapped('move_id'):
                        return_move.move_dest_ids.filtered(lambda m: m.state not in ('done', 'cancel'))._do_unreserve()
                    
                    picking_type_id = picking.picking_type_id.return_picking_type_id.id or picking.picking_type_id.id
                    
                    new_picking = picking.copy({
                        'move_lines': [],
                        'picking_type_id': picking_type_id,
                        'state': 'draft',
                        'origin': _("Return of %s") % picking.name,
                        'location_id': picking.location_dest_id.id,
                        'location_dest_id': location_id})
                    new_picking.message_post_with_view('mail.message_origin_link',
                        values={'self': new_picking, 'origin': picking},
                        subtype_id=self.env.ref('mail.mt_note').id)
                    returned_lines = 0
                    for return_line in self.product_return_moves:
                        if not return_line.move_id:
                            raise UserError(_("You have manually created product lines, please delete them to proceed"))
                        if return_line.quantity:
                            returned_lines += 1
                            
                            vals = self._prepare_move_default_values_inter(return_line, new_picking, picking)
                            r = return_line.move_id.copy(vals)
                            vals = {}

                            move_orig_to_link = return_line.move_id.move_dest_ids.mapped('returned_move_ids')
                            move_dest_to_link = return_line.move_id.move_orig_ids.mapped('returned_move_ids')
                            vals['move_orig_ids'] = [(4, m.id) for m in move_orig_to_link | return_line.move_id]
                            vals['move_dest_ids'] = [(4, m.id) for m in move_dest_to_link]

                            r.write(vals)
                    if not returned_lines:
                        raise UserError(_("Please specify at least one non-zero quantity."))
                    new_picking.action_confirm()
                    new_picking.action_assign()
                    self.product_return_moves.unlink()
                    for move in new_picking.move_line_ids:
                        move.write({'qty_done':move.product_uom_qty})
                    for move_line in new_picking.move_lines:
                        move_line.write({'quantity_done': move_line.product_uom_qty})
                    new_picking.button_validate()
                    self.write({'state':'process'})

    def ReturnDelivery(self):
        pickings = self.purchase_id.mapped('picking_ids')
        if pickings:
            for picking in pickings:
                if picking.state == 'done':
                    res = {}
                    product_return_moves = []
                    parent_location_id = False
                    location_id = False
                    original_location_id = False
                    res.update({'picking_id': picking.id})
                    for move in picking.move_lines:
                        for product in self.product_lines:
                            if move.product_id == product.product_id:
                                if move.scrapped:
                                    continue
                                if move.move_dest_ids:
                                    move_dest_exists = True

                                product_return_moves.append((0, 0, {'product_id': move.product_id.id, 'quantity': product.quantity, 'move_id': move.id, 'uom_id': move.product_id.uom_id.id}))
                    self.write({'product_return_moves' : product_return_moves})

                    location_id = picking.location_id.id
                    original_location_id = picking.location_id.id
                    parent_location_id = picking.picking_type_id.warehouse_id.view_location_id.id or picking.location_id.location_id.id
                    
                    for return_move in self.product_return_moves.mapped('move_id'):
                        return_move.move_dest_ids.filtered(lambda m: m.state not in ('done', 'cancel'))._do_unreserve()
                    
                    picking_type_id = picking.picking_type_id.return_picking_type_id.id or picking.picking_type_id.id
                    
                    new_picking = picking.copy({
                        'move_lines': [],
                        'picking_type_id': picking_type_id,
                        'state': 'draft',
                        'origin': _("Return of %s") % picking.name,
                        'location_id': picking.location_dest_id.id,
                        'location_dest_id': location_id})
                    new_picking.message_post_with_view('mail.message_origin_link',
                        values={'self': new_picking, 'origin': picking},
                        subtype_id=self.env.ref('mail.mt_note').id)
                    returned_lines = 0
                    for return_line in self.product_return_moves:
                        if not return_line.move_id:
                            raise UserError(_("You have manually created product lines, please delete them to proceed"))
                        if return_line.quantity:
                            returned_lines += 1
                            
                            vals = self._prepare_move_default_values_inter(return_line, new_picking, picking)
                            r = return_line.move_id.copy(vals)
                            vals = {}

                            move_orig_to_link = return_line.move_id.move_dest_ids.mapped('returned_move_ids')
                            move_dest_to_link = return_line.move_id.move_orig_ids.mapped('returned_move_ids')
                            vals['move_orig_ids'] = [(4, m.id) for m in move_orig_to_link | return_line.move_id]
                            vals['move_dest_ids'] = [(4, m.id) for m in move_dest_to_link]

                            r.write(vals)
                    if not returned_lines:
                        raise UserError(_("Please specify at least one non-zero quantity."))
                    new_picking.action_confirm()
                    new_picking.action_assign()
                    self.product_return_moves.unlink()
                    for move in new_picking.move_line_ids:
                        move.write({'qty_done':move.product_uom_qty})
                    for move_line in new_picking.move_lines:
                        move_line.write({'quantity_done': move_line.product_uom_qty})
                    new_picking.button_validate()
                    self.write({'state':'process'})

    def revertorder(self):
        if self.sale_id.id:
            
            self.ReturnPicking()
            self.CreateInvoiceCreditNote()
            
        if self.purchase_id.id:
            
            self.ReturnDelivery()
            self.CreateBillCreditNote()
            


class ReturnInterTransferCompanyLines(models.Model):
    _name = 'return.inter.transfer.company.line'
    _description = 'Return Inter Transfer Company Line'

    internal_id = fields.Many2one('inter.transfer.company')
    return_id = fields.Many2one('return.inter.transfer.company')
    product_id = fields.Many2one('product.product')
    quantity = fields.Integer('Quantity' , default= 1)
    price_unit = fields.Float('Price' , related = "product_id.lst_price")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: