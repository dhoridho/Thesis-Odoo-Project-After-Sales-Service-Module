import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError, Warning
import json

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    bill_consignment_ids = fields.Many2many("account.move", 'account_move_purchase_requisition_rel', 'move_id', 'requisition_id', string='Bill', copy=False)
    bill_consignment_count = fields.Integer('Bill Count') #(compute='_compute_bill_count')

    # @api.depends('bill_consignment_ids')
    # def _compute_bill_count(self):
    #     for record in self:
    #         count = 0
    #         if record.bill_consignment_ids:
    #             self.env.cr.execute("""
    #                 SELECT count(id)
    #                 FROM account_move
    #                 WHERE id in %s
    #             """ % (tuple(record.bill_consignment_ids.ids)))
    #             bill_consignment_count = self.env.cr.fetchall()
    #             count = bill_consignment_count[0][0] if bill_consignment_count else 0
    #         record.bill_consignment_count = count

    def action_confirm_approving(self):
        for record in self:
            if record.is_consignment:
                for rec in record.order_line:
                    if rec.price_unit < rec.last_purchase_price and record.is_consignment:
                        action = self.env.ref('equip3_inventory_consignment.action_wizard_for_process_consi')
                        result = action.read()[0]
                        imd = self.env['ir.model.data']
                        form_view_id = imd.xmlid_to_res_id('equip3_inventory_consignment.view_wizard_for_process_consi')
                        return {
                            'name': 'Warning',
                            'view_type': 'form',
                            'view_mode': 'form',
                            'views': [[form_view_id, 'form']],
                            'res_model': 'wizard.for.process.consi',
                            'type': 'ir.actions.act_window',
                            'target': 'new',
                        }

        return super(SaleOrder, self).action_confirm_approving()

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for rec in self:
            if rec.consignment_purchase_order_count:
                for line in rec.order_line:
                    if line.purchase_order_line_id:
                        line.product_id.write({
                            'sale_order_line_ids': [(4, line.id)],
                            'total_available_qty': line.product_id.total_available_qty - line.product_uom_qty,
                            'sale_qty': line.product_id.sale_qty + line.product_uom_qty,
                            'sale_price_total': line.product_id.sale_price_total + line.price_subtotal,
                        })
        return res


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    partner_id_product = fields.Many2one('res.partner')
    last_purchase_price = fields.Float('Last Purchase Price')
    is_consignment = fields.Boolean('Is Consignment')
    # purchase_requisition_id = fields.Many2one('purchase.requisition', string='Purchase Requisition')
    domain_purchase_requisition = fields.Char('domain requisition')
    is_billed_consignment = fields.Boolean('Is Billed Consignment', default=False)

    # consignment_id = fields.Many2one('consignment.agreement', string='Consignment Agreement')
    # domain_consignment_agreement = fields.Char('domain consignment_agreement', compute='_compute_consignment_id_domain')

    @api.onchange('product_template_id')
    def _onchange_product_template_id(self):
        for rec in self:
            if rec.product_template_id:
                product_id = self.env['product.product'].search([('product_tmpl_id', '=', rec.product_template_id.id),('is_consignment','=',True)])
                if product_id:
                    rec.is_consignment = True
                else:
                    rec.is_consignment = False
    #             consignment_line_id = self.env['consignment.agreement.line'].search([('product_id', 'in', product_id.ids)])
    #             consignment_id = self.env['consignment.agreement'].search(['&',
    #                                                                     ('line_ids', 'in', consignment_line_id.ids),
    #                                                                     ('state', '=', 'confirm')])
    #             if consignment_id:
    #                 rec.domain_consignment_agreement = json.dumps([('id', 'in', consignment_id.ids)])
    #             else:
    #                 rec.domain_consignment_agreement = json.dumps([('id', '=', 0)])
    #         else:
    #             rec.domain_consignment_agreement = json.dumps([('id', '=', 0)])



    # @api.depends('purchase_requisition_id','product_template_id')
    # def _compute_requisition_id_domain(self):
    #     for rec in self:
            # if rec.product_template_id and rec.order_id.is_consignment:
            #     product_id = self.env['product.product'].search([('product_tmpl_id', '=', rec.product_template_id.id)])
            #     # requisition_id = self.env['purchase.requisition'].search([('from_consignment', '=', True)])
            #     requisition_line_id = self.env['purchase.requisition.line'].search([('product_id', 'in', product_id.ids)])
            #     requisition_id = self.env['purchase.requisition'].search(['&','&',
            #                                                             ('from_consignment', '=', True),
            #                                                             ('line_ids', 'in', requisition_line_id.ids),
            #                                                             ('state_consignment', '=', 'confirm')])
            #     if requisition_id:
            #         rec.domain_purchase_requisition = json.dumps([('id', 'in', requisition_id.ids)])
            #     else:
            #         rec.domain_purchase_requisition = json.dumps([('id', '=', 0)])
            # else:
            # rec.domain_purchase_requisition = json.dumps([('id', '=', 0)])



    # @api.constrains('purchase_requisition_line_id')
    # def _check_requisition_in_consignment(self):
    #     for rec in self:
    #         if not rec.purchase_requisition_line_id and rec.order_id.is_consignment:
    #             raise ValidationError(_('You have to fill Purchase Requisition Id'))



    # domain_partner_id = fields.Char('Partner Domain', compute="_partner_id_domain")
    # stock_picking_id = fields.Many2one('stock.picking')

    # @api.depends('product_id')
    # def _partner_id_domain(self):
    #     for rec in self:
    #         if rec.order_id.is_consignment:
    #             rec.domain_partner_id = False
    #             stock_picking_id = self.env['stock.picking'].search(['&', '&',('picking_type_code', '=', 'incoming'),
    #                                                                 ('is_consignment', '=', True),
    #                                                                 ('state', '=', 'done')])
    #             product_id = self.env['product.product'].search([('product_tmpl_id', '=', rec.product_template_id.id)],limit = 1)
    #             stock_move = self.env['stock.move'].search([('product_id', '=', product_id.id),('picking_id', 'in', stock_picking_id.ids)])
    #             new_partner = stock_move.browse(stock_move.picking_id.owner_id.ids)
    #             rec.domain_partner_id = json.dumps([('id', 'in', new_partner.ids)])

    # @api.onchange('purchase_order_line_id')
    # def _onchange_purchase_order_line_id(self):
    #     for rec in self:
    #         if rec.purchase_order_line_id:
    #             po = self.env['purchase.order'].search([('id', '=', rec.purchase_order_line_id.order_id.id)])
    #             for x in po.picking_ids[0]:
    #                 rec.partner_id_product = x.owner_id.id
    #         purchase_order_line_id = self.env['purchase.order.line'].search([('id', '=', rec.purchase_order_line_id.id), ('product_id', '=', rec.product_id.id)])
    #         rec.last_purchase_price = purchase_order_line_id.price_unit

        # for rec in self:
        #     if rec.partner_id_product:
        #         print('======================================================================',rec.partner_id_product)
        #         stock_picking_id = self.env['stock.picking'].search(['&', '&',('picking_type_code', '=', 'incoming'),
        #                                                             ('is_consignment', '=', True),
        #                                                             ('state', '=', 'done')])
        #         product_id = self.env['product.product'].search([('product_tmpl_id', '=', self.product_template_id.id)],limit = 1)
        #         stock_move = self.env['stock.move'].search([('product_id', '=', product_id.id),('picking_id', 'in', stock_picking_id.ids)])
        #         purchase_line_ids = stock_move.browse(stock_move.picking_id.owner_id.ids)
        #         picking_ids_test = stock_move.browse(stock_move.picking_id.ids)
        #         # print('stock picking idsdsdsdsdsds',picking_ids_test)

        #         stock_move = self.env['stock.move'].search([('product_id', '=', product_id.id)])
        #         stock_picking_search = self.env['stock.picking'].search([('owner_id', '=', rec.partner_id_product.id)])
        #         print('stock_picking_searchstock_picking_search',stock_picking_search)


            # purchase_order =  self.env['purchase.order'].search([()])
            # purchase_order_line = self.env['purchase.order.line'].search([('product_id', '=', product_id.id),('is_consingment', '=', True)],limit=1)
            # rec.purchase_order_line_id = purchase_order_line.id
