# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields, api, _
from datetime import datetime, timedelta, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError


class Purchase(models.Model):
    _inherit = 'purchase.order'
    
    READONLY_STATES = {
        'purchase': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }
    def _domain_partner(self):
        return [('company_id','=',self.env.company.id),('vendor_sequence','!=',False)]
    partner_id = fields.Many2one('res.partner', string='Vendor', required=True, states=READONLY_STATES, change_default=True, tracking=True, domain=_domain_partner, help="You can find a vendor by its Name, TIN, Email or Internal Reference.") # ngga jalaln
    is_vendor_pricelist = fields.Boolean(string="Vendor Price List", compute="_compute_vendor_pricelist_po", store=False)

    @api.depends('partner_id')
    def _calculate_eval(self):
        for rec in self:
            end_date = date.today()
            rec.visible_eval = False
            start_date = end_date - timedelta(days=365)
            vendor_eval = self.env['vendor.evaluation'].search([
                        ('vendor', '=', rec.partner_id.id),
                        ('period_start', '>=', start_date),
                        ('period_end', '<=', end_date),
                        ('state', '=', 'approved')
                    ])
            if len(vendor_eval) > 0:
                total_final_point = sum(vendor_eval.mapped('final_point')) / len(vendor_eval)
                final_point = total_final_point if total_final_point > 0 else 0
                rec.visible_eval = str(round(final_point))

    def _compute_vendor_pricelist_po(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        self.is_vendor_pricelist = IrConfigParam.get_param('is_vendor_pricelist_approval_matrix', False)
        # self.is_vendor_pricelist = self.env.company.is_vendor_pricelist_approval_matrix

    @api.onchange('partner_id')
    def set_delivery_date_line(self):
        self._compute_vendor_pricelist_po()
        for res in self:
            if res.partner_id:
                products = []
                if res.order_line:
                    for line in res.order_line:
                        if line.product_template_id:
                            products.append(line.product_template_id.id)
                    list = ','.join(str(x) for x in products)
                    self._cr.execute("""
                        SELECT delay, product_tmpl_id, min_qty, price
                        FROM product_supplierinfo
                        WHERE name = '%s' and product_tmpl_id in (%s)
                    """ % (
                        res.partner_id.id,
                        list,
                    ))
                    lead = self._cr.dictfetchall()
                    if lead:
                        for i in res.order_line:
                            for j in lead:
                                if i.product_template_id.id == j['product_tmpl_id']:
                                    i.date_planned = datetime.now().date() +timedelta(days=j['delay'])
                                    if i.product_qty >= j['min_qty']:
                                        i.price_unit = j['price']

    @api.model
    def action_vendors_approve_menu(self):
        self.env.ref('equip3_purchase_masterdata.menu_vendor_to_approve').active = False

        irconfigparam = self.env['ir.config_parameter'].sudo()
        is_vendor_approval_matrix = irconfigparam.get_param('is_vendor_approval_matrix', False)
        # is_vendor_approval_matrix = self.env.company.is_vendor_approval_matrix
        if is_vendor_approval_matrix:
            self.env.ref('equip3_purchase_masterdata.menu_vendor_to_approve').active = True

    # Matikan auto create vendor pricelist (product.supplierinfo)
    def _add_supplier_to_product(self):
        pass

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    
    planned = fields.Date("Planned Date")
    is_vendor_pricelist_line = fields.Boolean(related="order_id.is_vendor_pricelist")

    def _suggest_quantity(self):
        '''
        Suggest a minimal quantity based on the seller
        '''
        if not self.product_id:
            return
        seller_min_qty = self.product_id.seller_ids \
            .filtered(lambda r: r.name == self.order_id.partner_id and (not r.product_id or r.product_id == self.product_id)) \
            .sorted(key=lambda r: r.min_qty)
        if seller_min_qty:
            if seller_min_qty[0].min_qty > 1:
                self.product_qty = 1.0
            else:
                self.product_qty = seller_min_qty[0].min_qty or 1.0
        else:
            self.product_qty = 1.0


    @api.onchange('product_template_id','product_qty')
    def set_delivery_date(self):
        for res in self:
            if res.product_template_id and res.order_id.partner_id:
                self._cr.execute("""
                        SELECT id, delay, min_qty, price
                        FROM product_supplierinfo
                        WHERE name = '%s' and product_tmpl_id = %s and company_id = %s
                    """ % (
                    res.order_id.partner_id.id,
                    res.product_template_id.id,
                    res.company_id.id
                ))
                vendor_pricelist = self._cr.dictfetchall()
                if vendor_pricelist:
                    for l in vendor_pricelist:
                        now = datetime.now().date()
                        vp = self.env['product.supplierinfo'].browse(l['id'])
                        result = False
                        res.planned = datetime.now().date() + timedelta(days=l['delay'])
                        if res.product_qty >= l['min_qty'] and vp:
                            if vp.date_start and vp.date_end:
                                if vp.date_start <= now <= vp.date_end:
                                    result = True
                                else:
                                    result = False
                            elif not vp.date_end and not vp.date_start:
                                result = True
                            else:
                                if vp.date_start:
                                    if vp.date_start <= now:
                                        result = True
                                    else:
                                        result = False
                                if vp.date_end:
                                    if now <= vp.date_end:
                                        result = True
                                    else:
                                        result = False
                            if result:
                                res.price_unit = l['price']
                            else:
                                res.price_unit = res.product_template_id.standard_price
                                
    # @api.onchange('date_planned')
    # def set_date_planned(self):
    # 	for res in self:
    # 		date = res.order_id.date_order
    # 		if res.date_planned != res.planned:
    # 			res.order_id.date_order = False
    # 			res.date_planned = res.planned
    # 			res.date_order = date
