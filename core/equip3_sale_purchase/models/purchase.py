from odoo import api, fields, models
import json

class Purchase(models.Model):
    _inherit = 'purchase.order'

    client_order_ref = fields.Char(string='Customer Reference', compute="_compute_customer_reference", store=True)
    is_dropship = fields.Boolean(string='Is Dropship', readonly=True)
    is_sale_order = fields.Boolean(string='Is Sale Order', default=False ,readonly=True)
    customer_partner_id = fields.Many2one(comodel_name='res.partner', string='Customer', readonly=True)
    customer_location_partner_id = fields.Many2one(comodel_name='res.partner', string='Customer Location', readonly=True)

    def _create_so_from_po(self , company):
        company_partner_id = self.partner_id.related_company_id
        current_company_id = self.env.company
        sale_order = self.env['sale.order']
        picking_validate = False
        invoice = False
        setting_id = self.env.company
        sale_order_line = self.env['sale.order.line']
        allowed_company_ids = [company_partner_id.id , current_company_id.id]
        so_vals = self.sudo().get_so_values(self.id , company_partner_id , current_company_id)
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
        so_id.with_context(allowed_company_ids=allowed_company_ids).sudo().action_confirm()

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

    def get_so_values(self , order_id , company_partner_id , current_company_id):
        res = super().get_so_values(order_id, company_partner_id, current_company_id)
        pricelist_id = self.env.company.product_pricelist_default.id
        if pricelist_id:
            pricelist_id = self.env['product.pricelist'].sudo().browse(int(pricelist_id))
            if pricelist_id.company_id != company_partner_id:
                pricelist_id = self.env['product.pricelist'].sudo().search([('company_id','=',company_partner_id.id)], limit=1)
        if not pricelist_id:
            pricelist_id = self.env['product.pricelist'].sudo().search([('company_id','=',False)], limit=1)
        
        partner_id = self.env['res.partner'].sudo().search([
            ('related_company_id', '=', current_company_id.id),
            ('company_id', '=', company_partner_id.id)
        ], limit=1)
        res['partner_invoice_id'] = partner_id.id
        res['partner_id'] = partner_id.id
        res['partner_shipping_id'] = partner_id.id
        res['fiscal_position_id'] = partner_id.property_account_position_id.id
        res['payment_term_id'] = partner_id.property_payment_term_id.id
        res['pricelist_id'] = partner_id.property_product_pricelist.id or pricelist_id.id
        res['branch_id'] = company_partner_id.intercompany_warehouse_id.sudo().branch_id.id
        res['warehouse_new_id'] = company_partner_id.intercompany_warehouse_id.id
        # res['account_tag_ids'] = self.env.user.analytic_tag_ids.filtered(lambda a:a.company_id and a.company_id.id == self.env.company.id).ids or self.env['account.analytic.tag'].search([('company_id','=',company_partner_id.id)], limit=1)
        return res

    # @api.model
    # def get_so_line_data(self, company, sale_id,line):
    #     res = super().get_so_line_data(company, sale_id, line)
    #     sale_id = self.env['sale.order'].browse(sale_id)
    #     res['delivery_address_id'] = line.destination_warehouse_id.id
    #     res['account_tag_ids'] = line.analytic_tag_ids.ids
    #     res['location_id'] = line.destination_warehouse_id.default_delivery_location_id.id
    #     return res
        
    @api.depends('sh_sale_order_id')
    def _compute_customer_reference(self):
        for rec in self:
            customer_reference = self.env['sale.order'].search([('id', '=', rec.sh_sale_order_id.id)])
            if customer_reference:
                rec.client_order_ref = customer_reference.client_order_ref
                rec.is_sale_order = True
            else:
                rec.client_order_ref = ''
                rec.is_sale_order = False

    def button_confirm(self):
        res = super(Purchase, self).button_confirm()
        for i in self:
            if i.is_dropship:
                do_ids = i.picking_ids.filtered(lambda r: r.state not in ('done', 'cancel'))
                location_virtual_customer = self.env.ref('stock.stock_location_customers')
                if do_ids:
                    do_ids.write({
                        'location_dest_id':location_virtual_customer.id,
                        'customer_partner_id':i.customer_partner_id.id,
                        'is_dropship':i.is_dropship,
                    })
                    sale = self.env['sale.order'].sudo()
                    source_1 = self.origin and self.origin.split('/') or []
                    if source_1:
                        if source_1[0] == 'PR':
                            pr_id = self.env['purchase.request'].sudo().search([
                                ('name','=',self.origin)
                            ],limit=1)
                            if pr_id and pr_id.origin:
                                sale = self.env['sale.order'].sudo().search([
                                    ('name','=',pr_id.origin)
                                ],limit=1)
                        elif source_1[0] == 'SO':
                            sale = self.env['sale.order'].sudo().search([
                                    ('name','=',self.origin)
                                ],limit=1)
                    if sale:
                        for picking in do_ids:
                            picking.sale_id = sale.id
                            if len(picking.move_ids_without_package) == len(sale.order_line):
                                for i in range(len(picking.move_ids_without_package)):
                                    picking.move_ids_without_package[i].sale_line_id = sale.order_line[i].id
        return res

