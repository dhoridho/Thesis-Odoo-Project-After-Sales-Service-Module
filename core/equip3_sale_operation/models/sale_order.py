# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


import logging
import re
from datetime import datetime, date

import pytz
import requests
from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError, Warning
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, float_compare

_logger = logging.getLogger(__name__)
from lxml import etree
import json as simplejson
import json
from operator import itemgetter
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from odoo.addons.equip3_approval_hierarchy.models.approval_hierarchy import ApprovalHierarchy


headers = {'content-type': 'application/json'}

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_external_link = fields.Boolean('Is External Link', default=False)

class ResUsers(models.Model):

    _inherit = "res.users"

    is_external_link = fields.Boolean('Is External Link', default=False)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        res = super(ResUsers, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                                  submenu=submenu)
        is_external_link = self.env.context.get("default_is_external_link")
        doc = etree.XML(res['arch'])
        if is_external_link and view_type == 'form':
            for node in doc.xpath("//field"):
                modifiers = simplejson.loads(node.get("modifiers"))
                modifiers['readonly'] = True
                node.set('modifiers', simplejson.dumps(modifiers))
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

class CrmTeam(models.Model):
    _inherit = "crm.team"

    is_external_link = fields.Boolean('Is External Link', default=False)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        res = super(CrmTeam, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                    submenu=submenu)
        is_external_link = self.env.context.get("default_is_external_link")
        doc = etree.XML(res['arch'])
        if is_external_link and view_type == 'form':
            for node in doc.xpath("//field"):
                modifiers = simplejson.loads(node.get("modifiers"))
                modifiers['readonly'] = True
                node.set('modifiers', simplejson.dumps(modifiers))
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

class CrmTag(models.Model):
    _inherit = "crm.tag"

    is_external_link = fields.Boolean('Is External Link', default=False)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        res = super(CrmTag, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                   submenu=submenu)
        is_external_link = self.env.context.get("default_is_external_link")
        doc = etree.XML(res['arch'])
        if is_external_link and view_type == 'form':
            for node in doc.xpath("//field"):
                modifiers = simplejson.loads(node.get("modifiers"))
                modifiers['readonly'] = True
                node.set('modifiers', simplejson.dumps(modifiers))
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

class AcruxChatConversation(models.Model):
    _inherit = 'acrux.chat.conversation'

    is_external_link = fields.Boolean('Is External Link', default=False)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        res = super(AcruxChatConversation, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                  submenu=submenu)
        is_external_link = self.env.context.get("default_is_external_link")
        doc = etree.XML(res['arch'])
        if is_external_link and view_type == 'form':
            for node in doc.xpath("//field"):
                modifiers = simplejson.loads(node.get("modifiers"))
                modifiers['readonly'] = True
                node.set('modifiers', simplejson.dumps(modifiers))
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

class Warehouse(models.Model):
    _inherit = "stock.warehouse"

    is_external_link = fields.Boolean('Is External Link', default=False)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        res = super(Warehouse, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                                 submenu=submenu)
        is_external_link = self.env.context.get("default_is_external_link")
        doc = etree.XML(res['arch'])
        if is_external_link and view_type == 'form':
            for node in doc.xpath("//field"):
                modifiers = simplejson.loads(node.get("modifiers"))
                modifiers['readonly'] = True
                node.set('modifiers', simplejson.dumps(modifiers))
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

class SaleOrderLine(models.Model):

    _name = 'sale.order.line'
    _inherit = ['sale.order.line','portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    product_template_id_domain = fields.Char(string="Product Domain")
    customer_id = fields.Many2one(related='order_id.partner_id', string='Customer')
    user_id = fields.Many2one(related='order_id.user_id', string='Salesperson')
    sequence_no = fields.Char(related='order_id.name', string="Sequence Number")
    product_id = fields.Many2one(
        'product.product', string='Product',
        change_default=True, ondelete='restrict', check_company=True,tracking=True)  # Unrequired company
    product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True, default=1.0,tracking=True)
    price_unit = fields.Float('Unit Price', required=True, digits='Product Price', default=0.0,tracking=True)
    customer_lead = fields.Float(
        'Lead Time', required=True, default=0.0,
        help="Number of days between the order confirmation and the shipping of the products to the customer",tracking=True)
    company_id = fields.Many2one(related='order_id.company_id', string='Company', store=True, readonly=True, index=True)
    name = fields.Text(string='Description', required=True,tracking=True)

    last_sale_price = fields.Float(string="Last Sale Price", related='product_id.last_sales_price', store=True)
    last_customer_sale_price = fields.Float(string="Last Sale Price Of Customer", compute='calculate_last_price_customer', store=True)
    account_tag_ids = fields.Many2many('account.analytic.tag', 'account_analytic_tag_order_line_rel', 'sale_line_id', 'tag_id', string="Analytic Group")
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")
    net_amount = fields.Monetary(string='Net Amount', compute='_get_net_amount', store=True)
    location_dest_id = fields.Many2one('stock.location', string="Delivery To")
    line_warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', related='line_warehouse_id_new', store=True) #gatau knapa pake yg new, tp saat onchange untuk memasukan value ke field ini, fieldnya selalu gak masuk dan tetap ambil value dari parent
    line_warehouse_id_new = fields.Many2one('stock.warehouse', string='Warehouse')
    filter_destination_warehouse = fields.Char(string="Filter Destination Warehouse",compute='_compute_filter_destination', store=False)
    branch_id = fields.Many2one('res.branch', related="order_id.branch_id", store=True)

    delivery_address_id = fields.Many2one('res.partner', string="Delivery Address")
    multiple_do_date = fields.Datetime(string='Delivery Date', index=True, copy=True)
    multiple_do_date_new = fields.Datetime(string='Delivery Date', index=True, copy=True)
    multi_discount = fields.Char('Multi Discount')
    discount_method = fields.Selection([('fix', 'Fixed'), ('per', 'Percentage')], 'Discount Method', default='fix', tracking=True)
    discount_amount = fields.Float('Discount Amount', tracking=True)
    filter_delivery_address_id = fields.Char(related="order_id.filter_delivery_address_id", string="Partner Address", store=True)
    hide_button_qa_sale = fields.Html(string='Hide Button', related='order_id.hide_button_qa_sale')
    trigger = fields.Boolean("Trigger", compute="", store=True)
    is_down_payment = fields.Boolean(string='Is Down Payment Invoice')
    product_template_id = fields.Many2one(
        'product.template', string='Product Template',
        related="product_id.product_tmpl_id", domain=[('sale_ok', '=', True)], tracking=True)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure', domain="[('category_id', '=', product_uom_category_id)]", tracking=True)
    tax_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)], tracking=True)
    res_product_uom = fields.Many2one('uom.uom', string='Unit of Measure', domain="[('category_id', '=', product_uom_category_id)]")
    brand_ids = fields.Many2many('product.brand', related='product_template_id.product_brand_ids', store=False)
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Untaxed Amount', readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total Amount', readonly=True, store=True)
    tax_discount_policy = fields.Selection(related='order_id.tax_discount_policy', store=True)
    discounted_value = fields.Monetary(compute='_compute_amount_disc_val', string='Discounted Value', readonly=True, store=True)
    is_recurring = fields.Boolean('Recurring Invoices')
    is_promotion_product_line = fields.Boolean('Is Promotion Product Line')
    is_promotion_disc_product_line = fields.Boolean('Is Promotion Disc Product Line')
    customer_city = fields.Char(string='Customer City', compute='_compute_customer_city_id', store=True)
    state_id = fields.Many2one('res.country.state', string='Customer States', related='order_id.partner_id.state_id', store=True)

    @api.depends('order_id.partner_id')
    def _compute_customer_city_id(self):
        for line in self:
            if line.order_id and line.order_id.partner_id:
                line.customer_city = line.order_id.partner_id.city
            else:
                line.customer_city = False

    @api.depends('company_id','branch_id')
    def _compute_filter_destination(self):
        for rec in self:
            if rec.branch_id:
                rec.filter_destination_warehouse = json.dumps([('branch_id', '=', rec.branch_id.id), ('company_id', '=', rec.company_id.id),('id','in',self.env.user.warehouse_ids.ids)])
            else:
                rec.filter_destination_warehouse = json.dumps([('id', 'in', 0)])

    @api.onchange('product_id','line_warehouse_id_new','delivery_address_id','multiple_do_date','multiple_do_date_new')
    def check_sale_line(self):
        self.ensure_one()
        if self.user_has_groups('equip3_sale_operation.group_multi_do'):
            if self.product_id and self.line_warehouse_id and self.multiple_do_date and self.delivery_address_id:
                self.order_id.check_sale_line()
        else:
            if self.product_id and self.line_warehouse_id:
                self.order_id.check_sale_line()

    @api.onchange('price_unit', 'order_id')
    def _check_partner_pricelist(self):
        for rec in self:
            if not rec.order_id.partner_id or not rec.order_id.pricelist_id:
                if not rec.order_id.partner_id:
                    raise ValidationError("Please set the Customer to continue")
                if not rec.order_id.pricelist_id:
                    raise ValidationError("Please set the pricelist to continue")
            else:
                break

    @api.onchange('price_unit', 'order_id')
    def _check_product_price(self):
        for record in self:
            sale_product_id = record.product_id.id
            sale_price_unit = record.price_unit
            sale_product_uom = record.product_uom.id
            sale_min_qty = record.product_uom_qty #changed
            sale_order_date = record.order_id.date_order
            margin = record.margin / record.product_uom_qty
            if sale_product_id and len(record.order_id.pricelist_id.item_ids) > 0:
                for list_items in record.order_id.pricelist_id.item_ids.filtered(lambda x:x.pricelist_uom_id.id == sale_product_uom):
                    item_uom = list_items.pricelist_uom_id.id
                    min_price = list_items.minimum_price
                    max_price = list_items.maximum_price
                    item_min_qty = list_items.min_quantity
                    item_date_start = list_items.date_start
                    item_date_end = list_items.date_end
                    if item_uom:
                        if sale_product_uom != item_uom:
                            sale_min_qty = record.product_uom._compute_quantity(sale_min_qty, list_items.pricelist_uom_id)
                            sale_product_uom = item_uom
                            sale_price_unit = sale_price_unit / (sale_min_qty / record.product_uom_qty)
                            margin = record.margin / sale_min_qty
                    check_min_max = False
                    if list_items.applied_on == '3_global':
                            if item_uom and item_min_qty and item_date_start and item_date_end:
                                if sale_product_uom == item_uom and sale_min_qty >= item_min_qty \
                                        and sale_order_date >= item_date_start and sale_order_date <= item_date_end:
                                    check_min_max = True
                            elif item_uom and item_min_qty and item_date_start:
                                if sale_product_uom == item_uom and sale_min_qty >= item_min_qty \
                                        and sale_order_date >= item_date_start:
                                    check_min_max = True
                            elif item_uom and item_min_qty and item_date_end:
                                if sale_product_uom == item_uom and sale_min_qty >= item_min_qty \
                                        and sale_order_date <= item_date_end:
                                    check_min_max = True
                            elif item_uom and item_min_qty:
                                if sale_product_uom == item_uom and sale_min_qty >= item_min_qty:
                                    check_min_max = True

                            elif item_min_qty and item_date_start and item_date_end:
                                if sale_min_qty >= item_min_qty and sale_order_date >= item_date_start and sale_order_date <= item_date_end:
                                    check_min_max = True
                            elif item_min_qty and item_date_start:
                                if sale_min_qty >= item_min_qty and sale_order_date >= item_date_start:
                                    check_min_max = True
                            elif item_min_qty and item_date_end:
                                if sale_min_qty >= item_min_qty and sale_order_date <= item_date_end:
                                    check_min_max = True

                            elif sale_min_qty >= item_min_qty:
                                    check_min_max = True

                    elif list_items.applied_on == '0_product_variant':
                        price_product_id = list_items.product_id.id
                        if not item_uom:
                            item_uom = list_items.product_id.uom_id.id
                            if sale_product_uom != item_uom:
                                sale_min_qty = record.product_uom._compute_quantity(sale_min_qty, list_items.product_id.uom_id)
                                sale_product_uom = item_uom
                                sale_price_unit = sale_price_unit / (sale_min_qty / record.product_uom_qty)
                                margin = record.margin / sale_min_qty
                        if sale_product_id == price_product_id:
                            if item_uom and item_min_qty and item_date_start and item_date_end:
                                if sale_product_uom == item_uom and sale_min_qty >= item_min_qty \
                                        and sale_order_date >= item_date_start and sale_order_date <= item_date_end:
                                    check_min_max = True
                            elif item_uom and item_min_qty and item_date_start:
                                if sale_product_uom == item_uom and sale_min_qty >= item_min_qty \
                                        and sale_order_date >= item_date_start:
                                    check_min_max = True
                            elif item_uom and item_min_qty and item_date_end:
                                if sale_product_uom == item_uom and sale_min_qty >= item_min_qty \
                                        and sale_order_date <= item_date_end:
                                    check_min_max = True
                            elif item_uom and item_min_qty:
                                if sale_product_uom == item_uom and sale_min_qty >= item_min_qty:
                                    check_min_max = True

                            elif item_min_qty and item_date_start and item_date_end:
                                if sale_min_qty >= item_min_qty and sale_order_date >= item_date_start and sale_order_date <= item_date_end:
                                    check_min_max = True
                            elif item_min_qty and item_date_start:
                                if sale_min_qty >= item_min_qty and sale_order_date >= item_date_start:
                                    check_min_max = True
                            elif item_min_qty and item_date_end:
                                if sale_min_qty >= item_min_qty and sale_order_date <= item_date_end:
                                    check_min_max = True

                            elif sale_min_qty >= item_min_qty:
                                    check_min_max = True

                    elif list_items.applied_on == '1_product':
                        sale_product_id = record.product_template_id.id
                        price_product_id = list_items.product_tmpl_id.id
                        if not item_uom:
                            item_uom = list_items.product_tmpl_id.uom_id.id
                            if sale_product_uom != item_uom:
                                sale_min_qty = record.product_uom._compute_quantity(sale_min_qty, list_items.product_tmpl_id.uom_id)
                                sale_product_uom = item_uom
                                sale_price_unit = sale_price_unit / (sale_min_qty / record.product_uom_qty)
                                margin = record.margin / sale_min_qty
                        if sale_product_id == price_product_id:
                            if item_uom and item_min_qty and item_date_start and item_date_end:
                                if sale_product_uom == item_uom and sale_min_qty >= item_min_qty \
                                        and sale_order_date >= item_date_start and sale_order_date <= item_date_end:
                                    check_min_max = True
                            elif item_uom and item_min_qty and item_date_start:
                                if sale_product_uom == item_uom and sale_min_qty >= item_min_qty \
                                        and sale_order_date >= item_date_start:
                                    check_min_max = True
                            elif item_uom and item_min_qty and item_date_end:
                                if sale_product_uom == item_uom and sale_min_qty >= item_min_qty \
                                        and sale_order_date <= item_date_end:
                                    check_min_max = True
                            elif item_uom and item_min_qty:
                                if sale_product_uom == item_uom and sale_min_qty >= item_min_qty:
                                    check_min_max = True

                            elif item_min_qty and item_date_start and item_date_end:
                                if sale_min_qty >= item_min_qty and sale_order_date >= item_date_start and sale_order_date <= item_date_end:
                                    check_min_max = True
                            elif item_min_qty and item_date_start:
                                if sale_min_qty >= item_min_qty and sale_order_date >= item_date_start:
                                    check_min_max = True
                            elif item_min_qty and item_date_end:
                                if sale_min_qty >= item_min_qty and sale_order_date <= item_date_end:
                                    check_min_max = True

                            elif sale_min_qty >= item_min_qty:
                                    check_min_max = True

                    elif list_items.applied_on == '2_product_category':
                        sale_categ_id = record.product_id.categ_id.id
                        price_categ_id = list_items.categ_id.id
                        if sale_categ_id == price_categ_id:
                            if item_uom and item_min_qty and item_date_start and item_date_end:
                                if sale_product_uom == item_uom and sale_min_qty >= item_min_qty \
                                        and sale_order_date >= item_date_start and sale_order_date <= item_date_end:
                                    check_min_max = True
                            elif item_uom and item_min_qty and item_date_start:
                                if sale_product_uom == item_uom and sale_min_qty >= item_min_qty \
                                        and sale_order_date >= item_date_start:
                                    check_min_max = True
                            elif item_uom and item_min_qty and item_date_end:
                                if sale_product_uom == item_uom and sale_min_qty >= item_min_qty \
                                        and sale_order_date <= item_date_end:
                                    check_min_max = True
                            elif item_uom and item_min_qty:
                                if sale_product_uom == item_uom and sale_min_qty >= item_min_qty:
                                    check_min_max = True

                            elif item_min_qty and item_date_start and item_date_end:
                                if sale_min_qty >= item_min_qty and sale_order_date >= item_date_start and sale_order_date <= item_date_end:
                                    check_min_max = True
                            elif item_min_qty and item_date_start:
                                if sale_min_qty >= item_min_qty and sale_order_date >= item_date_start:
                                    check_min_max = True
                            elif item_min_qty and item_date_end:
                                if sale_min_qty >= item_min_qty and sale_order_date <= item_date_end:
                                    check_min_max = True

                            elif sale_min_qty >= item_min_qty:
                                    check_min_max = True

                    product_name = f"[{record.product_id.default_code}] {record.product_id.name}"
                    if check_min_max and min_price > 0 and max_price > 0:
                        if (sale_price_unit < min_price):
                            raise Warning(f"{product_name} unit price is below the minimum price")
                        if (sale_price_unit > max_price):
                            raise Warning(f"{product_name} unit price is above the maximum price")
                        # break
                    elif check_min_max and min_price > 0:
                        if (sale_price_unit < min_price):
                            raise Warning(f"{product_name} unit price is below the minimum price")
                        # break
                    elif check_min_max and max_price > 0:
                        if (sale_price_unit > max_price):
                            raise Warning(f"{product_name} unit price is above the maximum price")
                        # break
                    if list_items.compute_price == 'formula' and check_min_max:
                        min_margin = list_items.price_min_margin
                        max_margin = list_items.price_max_margin
                        if min_margin > 0:
                            if margin < min_margin:
                                raise Warning(f"{product_name} margin is below the minimum margin on the selected pricelist")
                        if max_margin > 0:
                            if margin > max_margin:
                                raise Warning(f"{product_name} margin is above the maximum margin on the selected pricelist")

    @api.depends('invoice_lines.move_id.state', 'invoice_lines.quantity', 'untaxed_amount_to_invoice')
    def _get_invoice_qty(self):
        res = super()._get_invoice_qty()
        order = self[0].order_id
        inv = order.invoice_ids
        is_dp = order.is_down_payment
        if inv and is_dp:
            self.env.cr.execute("""
                SELECT id
                FROM sale_order_line
                WHERE order_id = %s and is_down_payment = True
            """ % (order.id))
            line_dp_id = self.env.cr.fetchall()
            if line_dp_id:
                for line in line_dp_id:
                    self._cr.execute("""UPDATE sale_order_line SET qty_invoiced = product_uom_qty WHERE id = %s""" % line[0])
                    self._cr.commit()
        return res

    @api.onchange('discount_method')
    def set_disc_value(self):
        for rec in self:
            rec.write({
                'discount_amount': 0,
                'multi_discount': "0",
                'discounted_value': 0,
            })

    @api.depends('discount_amount', 'multi_discount', 'product_uom_qty', 'price_unit')
    def _compute_amount_disc_val(self):
        # tax_discount_policy = self.env.company.tax_discount_policy or False
        for rec in self:
            tax_discount_policy = rec.tax_discount_policy
            gross_total = rec.product_uom_qty * rec.price_unit
            if tax_discount_policy == 'tax':
                if rec.discount_type == 'global':
                    if rec.discount_method == 'fix':
                        rec.discounted_value = rec.discount_amount
                    else:
                        rec.discounted_value = (gross_total + rec.price_tax) * (rec.discount_amount / 100)
                else:
                    if rec.discount_method == 'fix':
                        rec.discounted_value = rec.discount_amount
                    else:
                        rec.discounted_value = gross_total * (rec.discount_amount / 100)
            else:
                if rec.discount_method == 'fix':
                    rec.discounted_value = rec.discount_amount
                else:
                    rec.discounted_value = gross_total * (rec.discount_amount / 100)

    def _prepare_invoice_line(self,**optional_values):
        if self.product_id.invoice_policy != 'order' and not self.qty_to_invoice:
            raise ValidationError('Please make a delivery for the sale order first.')
        res = super()._prepare_invoice_line(**optional_values)
        res['analytic_tag_ids'] = [(6, 0, self.account_tag_ids.ids)]
        if 'is_dp' in self.env.context:
            if not self.env.context.get('is_dp'):
                if 'Down Payment' in res['name']:
                    res['quantity'] = 1
                    res['is_down_payment'] = True
                    res['sale_line_ids'] = False
                    res['price_unit'] = -(res['price_unit'])
                if 'Recurring' in res['name']:
                    res['quantity'] = self.product_uom_qty
                    res['price_unit'] = -(res['price_unit'])
        if 'is_deduct_recurring' in self.env.context:
            if self.env.context['policy'] == 'order':
                res['quantity'] = self.product_uom_qty

        free_delivery_product = self.env.ref('delivery.product_product_delivery')
        if self.product_id == free_delivery_product:
            res['discount_method'] = False
        if 'is_recurring' in self.env.context:
        #     # untuk mengatasi perbedaan karna pembulatan
            res['quantity'] = self.product_uom_qty
        #     # -------------------
        #     discount_amount = round(self.discount_amount / self.order_id.total_recurring, 2)
        #     discount_amt = round(self.discount_amt / self.order_id.total_recurring, 2)
        #     res['discount_amount'] = discount_amount if len(self.order_id.invoice_ids) != self.order_id.total_invoice - 1 else round(self.discount_amount - (discount_amount * (self.order_id.total_invoice - 1)),2)
        #     res['discount_amt'] = discount_amt if len(self.order_id.invoice_ids) != self.order_id.total_invoice - 1 else round(self.discount_amt - (discount_amt * (self.order_id.total_invoice - 1)),2)
        #     res['price_unit'] = self.price_unit
        #     if self.is_down_payment:
        #         if len(self.order_id.invoice_ids) == self.order_id.total_invoice - 1:
        #             quantity = round(1 - (1/self.order_id.total_recurring * (self.order_id.total_recurring-1)),2)
        #             res['quantity'] = quantity
        #         res['price_unit'] = -(self.price_total)
        return res

    # @api.onchange('product_uom','product_id')
    # def change_qty(self):
    #     for rec in self:
    #         if rec.res_product_uom:
    #             ref_qty = rec.product_uom_qty / rec.res_product_uom.factor
    #             qty = ref_qty * rec.product_uom.factor
    #             rec.product_uom_qty = qty
    #         rec.res_product_uom = rec.product_uom

    @api.model
    def create(self, vals):
        res = super(SaleOrderLine, self).create(vals)
        # res.order_id._reset_sequence()
        return res

    # add tracking on sales.order form - order lines
    # def write(self, vals):
    #     super().write(vals)
    #     if set(vals) & set(self._get_tracked_fields()):
    #         self._track_changes(self.order_id)

    def unlink(self):
        order_seq = self.order_id
        res = super(SaleOrderLine, self).unlink()
        order_seq._reset_sequence()
        return res

    # def _track_changes(self, order_id):
    #     if self.message_ids:
    #         message_id = order_id.message_post(body=f'<strong>{ self._description }:</strong> { self.display_name }').id
    #         self.env.cr.execute("""
    #             SELECT id
    #             FROM mail_tracking_value
    #             WHERE mail_message_id = %s
    #         """ % (self.message_ids[0].id))
    #         trackings = self.env.cr.fetchall()
    #         # trackings = self.env['mail.tracking.value'].sudo().search([('mail_message_id', '=', self.message_ids[0].id)])
    #         for tracking in trackings:
    #             tracking.copy({'mail_message_id': message_id})

    # @api.depends('product_id')
    # def _compute_qty_delivered_method(self):
    #     res = super(SaleOrderLine, self)._compute_qty_delivered_method()
    #     IrConfigParam = self.env['ir.config_parameter'].sudo()
    #     # product_service_operation_delivery = bool(IrConfigParam.get_param('is_product_service_operation_delivery', False))
    #     order_id = self[0].order_id
    #     if isinstance(self[0].id, models.NewId):
    #         for line in self:
    #             if not line.is_expense and ((line.product_id.type in ['service'] and line.product_id.is_product_service_operation_delivery) or line.product_id.type in ['consu', 'product','asset']):
    #                 line.qty_delivered_method = 'stock_move'
    #     else:
    #         self.env.cr.execute("""
    #             SELECT s.id
    #             FROM sale_order_line as s
    #             INNER JOIN product_product as p
    #             ON s.product_id = p.id
    #             INNER JOIN product_template as pt
    #             ON p.product_tmpl_id = pt.id
    #             WHERE s.is_expense = False and ((pt.type = 'service' and pt.is_product_service_operation_delivery = True) or pt.type in ('consu', 'product','asset')) and s.order_id = %s
    #         """ % (order_id.id))
    #         order_line = self.env.cr.fetchall()
    #         if order_line:
    #             self._cr.execute("""UPDATE sale_order_line SET qty_delivered_method = 'stock_move' WHERE id = %s""", (tuple(order_line[-1])))
    #             self._cr.commit()
    #     return res

    @api.depends('product_id')
    def _compute_qty_delivered_method(self):
        res = super(SaleOrderLine, self)._compute_qty_delivered_method()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        # product_service_operation_delivery = bool(IrConfigParam.get_param('is_product_service_operation_delivery', False))
        for line in self:
            if not line.is_expense and ((line.product_id.type in ['service'] and line.product_id.is_product_service_operation_delivery) or line.product_id.type in ['consu', 'product','asset']):
                line.qty_delivered_method = 'stock_move'
        return res

    @api.depends('move_ids.state', 'move_ids.scrapped', 'move_ids.product_uom_qty', 'move_ids.product_uom')
    def _compute_qty_delivered(self):
        res = super(SaleOrderLine, self)._compute_qty_delivered()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        order_id = self[0].order_id
        if order_id.state in ('sale','done'):
            order_line = False
            if bool(self.env['ir.config_parameter'].sudo().get_param('is_product_service_operation_delivery')):
                self.env.cr.execute("""
                    SELECT s.id
                    FROM sale_order_line as s
                    INNER JOIN product_product as p
                    ON s.product_id = p.id
                    INNER JOIN product_template as pt
                    ON p.product_tmpl_id = pt.id
                    WHERE pt.type = 'service' and pt.is_product_service_operation_delivery = False and s.order_id = %s
                """ % (order_id.id))
                order_line = self.env.cr.fetchall()
            else:
                self.env.cr.execute("""
                    SELECT s.id
                    FROM sale_order_line as s
                    INNER JOIN product_product as p
                    ON s.product_id = p.id
                    INNER JOIN product_template as pt
                    ON p.product_tmpl_id = pt.id
                    WHERE pt.type = 'service' and s.order_id = %s
                """ % (order_id.id))
                order_line = self.env.cr.fetchall()
            if order_line:
                for oline in order_line:
                    self._cr.execute("""UPDATE sale_order_line SET qty_delivered = product_uom_qty WHERE id = %s""", (tuple(oline)))
                    self._cr.commit()
        return res

    # @api.onchange('line_warehouse_id_new')
    # def set_warehouse_id(self):
    #     for line in self:
    #         if not line.order_id.is_single_warehouse:
    #             if line.line_warehouse_id_new != line.line_warehouse_id:
    #                 line.line_warehouse_id = line.line_warehouse_id_new

    # @api.depends('multiple_do_date','multiple_do_date_new')
    # def _compute_do_date(self):
    #     for rec in self:
    #         if rec.multiple_do_date and not rec.multiple_do_date_new:
    #             rec.multiple_do_date_new = rec.multiple_do_date
    #         elif rec.multiple_do_date_new and not rec.multiple_do_date:
    #             rec.multiple_do_date = rec.multiple_do_date_new
    #         elif rec.multiple_do_date_new != rec.multiple_do_date:
    #             rec.multiple_do_date = rec.multiple_do_date_new
    #         rec.trigger = True

    @api.onchange('multiple_do_date','multiple_do_date_new')
    def set_do_date(self):
        for rec in self:
            if rec.multiple_do_date and not rec.multiple_do_date_new:
                rec.multiple_do_date_new = rec.multiple_do_date
            elif rec.multiple_do_date_new and not rec.multiple_do_date:
                rec.multiple_do_date = rec.multiple_do_date_new
            elif rec.multiple_do_date_new != rec.multiple_do_date:
                rec.multiple_do_date = rec.multiple_do_date_new

    def set_price_include(self, price, price_include):
        tax_pph = 0
        total_tax = self.set_taxes(price)
        taxes_pph = []
        if price_include:
            for i in self.tax_id:
                if i.amount < 0:
                    taxes_pph.append(i.compute_all(price - total_tax, self.order_id.currency_id, 1, product=self.product_id, partner=self.order_id.partner_id)['taxes'])
            if taxes_pph:
                for i in taxes_pph:
                    tax_pph += i[0]['amount']
            price_tax = total_tax + tax_pph
            return {
                'price_tax': price_tax,
                'price_total': price + tax_pph,
                'price_subtotal': price - total_tax
            }
        else:
            price_tax = total_tax + tax_pph
            return {
                'price_tax': price_tax,
                'price_total': price + price_tax,
                'price_subtotal': price
            }

    def set_taxes(self, price_subtotal):
        total_tax = 0
        taxes = []
        for i in self.tax_id:
            if i.amount > 0:
                taxes.append(i.compute_all(price_subtotal, self.order_id.currency_id, 1, product=self.product_id, partner=self.order_id.partner_id)['taxes'])
        for i in taxes:
            total_tax += i[0]['amount']
        return total_tax


    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id','discount_amount')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            res_config= self.env['ir.config_parameter'].sudo().search([],order="id desc", limit=1)
            if res_config:
                # tax_discount_policy = self.env.company.tax_discount_policy or False
                tax_discount_policy = line.tax_discount_policy
                if tax_discount_policy == 'untax':
                    if line.discount_type == 'line':
                        if line.discount_method == 'fix':
                            price = (line.price_unit * line.product_uom_qty) - line.discounted_value
                            price_include = False
                            for i in line.tax_id:
                                if i.price_include:
                                    price_include = True
                            value = line.set_price_include(price, price_include)
                            line.write({
                                'price_tax': value['price_tax'],
                                'price_total': value['price_total'], # - line.discount_amount,
                                'price_subtotal': value['price_subtotal'], # - line.discount_amount,
                                'discount_amt': line.discount_amount,
                            })

                        elif line.discount_method == 'per':
                            price = (line.price_unit * line.product_uom_qty) * (1 - (line.discount_amount or 0.0) / 100.0)
                            price_x = ((line.price_unit * line.product_uom_qty) - (line.price_unit * line.product_uom_qty) * (1 - (line.discount_amount or 0.0) / 100.0))
                            price_include = False
                            for i in line.tax_id:
                                if i.price_include:
                                    price_include = True
                            value = line.set_price_include(price, price_include)
                            line.write({
                                'price_tax': value['price_tax'],
                                'price_total': value['price_total'], # - price_x,
                                'price_subtotal': value['price_subtotal'],
                                'discount_amt': price_x,
                            })
                        else:
                            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                            price_include = False
                            for i in line.tax_id:
                                if i.price_include:
                                    price_include = True
                            value = line.set_price_include(price, price_include)
                            line.write({
                                'price_tax': value['price_tax'],
                                'price_total': value['price_total'],
                                'price_subtotal': value['price_subtotal'],
                            })
                    else:
                        total_price = line.price_unit * line.product_uom_qty
                        tax_per = 0
                        if line.tax_id:
                            for tax in line.tax_id:
                                if tax.amount_type == 'percent':
                                    tax_per += tax.amount
                        price = total_price-line.discounted_value
                        price_include = False
                        for i in line.tax_id:
                            if i.price_include:
                                price_include = True
                        value = line.set_price_include(price, price_include)
                        line.write({
                            'price_tax': value['price_tax'],
                            'price_total': value['price_total'],
                            'price_subtotal': value['price_subtotal'],
                        })
                elif tax_discount_policy == 'tax':
                    if line.discount_type == 'line':
                        price_x = 0.0
                        price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                        taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)

                        if line.discount_method == 'fix':
                            price_x = (taxes['total_included']) - (taxes['total_included'] - line.discount_amount)
                        elif line.discount_method == 'per':
                            price_x = (taxes['total_included']) - (taxes['total_included'] * (1 - (line.discount_amount or 0.0) / 100.0))
                        else:
                            price_x = line.price_unit * (1 - (line.discount or 0.0) / 100.0)

                        line.write({
                            'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                            'price_total': taxes['total_included'] - line.discounted_value,
                            'price_subtotal': taxes['total_excluded'],
                            'discount_amt': price_x,
                        })
                    else:
                        price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                        taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)
                        price_tax = sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                        if line.discount_method == 'fix':
                            price_total = taxes['total_included'] - line.discounted_value
                        else:
                            price_total = ((line.price_unit * line.product_uom_qty)+price_tax) - ((((line.price_unit * line.product_uom_qty)+price_tax)*line.discount_amount)/100)
                        line.write({
                            'price_tax': price_tax,
                            'price_total': price_total,
                            'price_subtotal': taxes['total_excluded'],
                        })
                else:
                    price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)

                    line.write({
                        'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                        'price_total': taxes['total_included'],
                        'price_subtotal': taxes['total_excluded'],
                    })
            else:
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)

                line.write({
                    'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                    'price_total': taxes['total_included'],
                    'price_subtotal': taxes['total_excluded'],
                })
            # line.order_id._amount_all()

    def get_disocunt(self,percentage,amount):
        new_amount = (percentage * amount)/100
        return (amount - new_amount)

    @api.onchange('multi_discount')
    def _onchange_multi_discount(self):
        if self.discount_method == 'per' and self.product_template_id:
            if self.multi_discount:
                amount = 100
                discount_amount = 0
                splited_discounts = self.multi_discount.split("+")
                for disocunt in splited_discounts:
                    try:
                        amount = self.get_disocunt(float(disocunt),amount)
                    except ValueError:
                        raise ValidationError("Please Enter Valid Multi Discount")
                discount_amount = 100 - amount
                if 0 < discount_amount < 100:
                    self.discount_amount = discount_amount
                else:
                    raise ValidationError("Please Enter Valid Multi Discount")
            else:
                self.discount_amount = 0

    @api.onchange('product_uom_qty')
    def set_default_multi_disc(self):
        for res in self:
            if res.order_id.discount_type == 'global':
                res.discount_method = res.order_id.discount_method
                res.discount_amount = res.order_id.discount_amount
                # if res.order_id.multilevel_disc:
                #     res.multi_discount = res.order_id.multi_discount
                res.multi_discount = res.order_id.multi_discount

    @api.onchange('product_uom_qty')
    def set_address(self):
        deliv = 0
        inv = 0
        if self.order_id.partner_id.child_ids:
            for line in self.order_id.partner_id.child_ids:
                if line.type == 'delivery':
                    deliv += 1
            if deliv < 1:
                self.delivery_address_id = self.order_id.partner_id.id


    @api.onchange('sequence','company_id')
    def set_account_group(self):
        for res in self:
            res.account_tag_ids = res.order_id.account_tag_ids
            # if not res.line_warehouse_id_new:
            #     res.line_warehouse_id = res.order_id.warehouse_id
            # else:
            #     res.line_warehouse_id = res.line_warehouse_id_new
            res.line_warehouse_id_new = res.order_id.warehouse_id
            if res.order_id.is_single_delivery_date:
                res.multiple_do_date = res.order_id.commitment_date

    @api.depends('price_subtotal', 'product_uom_qty', 'price_reduce_taxinc')
    def _get_net_amount(self):
        for res in self:
            res.net_amount = res.price_reduce_taxinc * res.product_uom_qty

    @api.model
    def default_get(self, fields):
        res = super(SaleOrderLine, self).default_get(fields)
        context = dict(self.env.context) or {}
        if context.get('brand_id'):
            res['product_template_id_domain'] = json.dumps([('product_brand_ids', 'in', [context.get('brand_id')]),('sale_ok', '=', True),('type','!=','asset')])
        else:
            res['product_template_id_domain'] = json.dumps([('sale_ok', '=', True), ('type','!=','asset'), '|', ('company_ids', '=', False), ('company_ids', 'in', self.env.company.id)])
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            next_sequence2 = 1
            if 'order_line' in context_keys:
                if len(self._context.get('order_line')) > 0:
                    next_sequence = len(self._context.get('order_line')) + 1
                for line in self._context.get('order_line'):
                    if 'virtual' in str(line[1]):
                        # if line[2]['product_template_id']:
                        if line[2]['product_id']:
                            next_sequence2 += 1
                    else:
                        if self.env['sale.order.line'].browse(line[1]).product_template_id:
                            next_sequence2 += 1
            res.update({'sequence': next_sequence, 'sale_line_sequence': next_sequence2})
        return res

    sale_line_sequence = fields.Char(string='No')

    @api.onchange('product_id')
    def product_id_change(self):
        if self.customer_id:
            # partner_delivery_ids = self.env['res.partner'].search([('parent_id', '=', self.customer_id.id), ('type', '=', 'delivery')], limit=1).ids
            self.env.cr.execute("""
                SELECT id
                FROM res_partner
                WHERE parent_id = %s and type = 'delivery' ORDER BY id DESC limit 1
            """ % (self.customer_id.id))
            partner_delivery_id = self.env.cr.fetchall()
            if partner_delivery_id:
                self.delivery_address_id = partner_delivery_id[0][0]
            else:
                self.delivery_address_id = self.customer_id.id

        res = super(SaleOrderLine, self).product_id_change()
        name = self.product_id and self.product_id.display_name or ''
        name = name.split('] ')[-1]
        if self.product_id.description_sale:
            name = name + " " + self.product_id.description_sale
        self.name = name
        # self._compute_partner_address()
        return res

    # sudah ada di sale.order
    # def _compute_partner_address(self):
    #     for record in self:
    #         partner_ids = record.customer_id.child_ids.filtered(lambda r: r.type == 'delivery')
    #         if record.customer_id and record.customer_id.child_ids and partner_ids:
    #             record.filter_delivery_address_id = [(6, 0, partner_ids.ids)]
    #         else:
    #             record.filter_delivery_address_id = [(6, 0, record.customer_id.ids)]

    # sudah ada last sale price pada product
    # @api.depends('product_id')
    # def calculate_last_price(self):
    #     for record in self:
    #         if isinstance(record.id, models.NewId):
    #             sale_order_line_id = self.search([('state','in',('sale','done')),('product_id', '=', record.product_id.id)], limit=1, order="id desc")
    #         else:
    #             sale_order_line_id = self.search([('state','in',('sale','done')),('product_id', '=', record.product_id.id), ('id', '!=', record.id)], limit=1, order="id desc")
    #         record.last_sale_price = sale_order_line_id.price_unit

    @api.depends('product_id', 'order_id', 'order_id.partner_id')
    def calculate_last_price_customer(self):
        list_product = []
        for record in self:
            price = 0
            if record.product_id and record.product_id.id not in list_product:
                if isinstance(record.id, models.NewId):
                    # sale_order_line_id = self.search([('state','in',('sale','done')),('product_id', '=', record.product_id.id), ('order_id.partner_id', '=', record.order_id.partner_id.id)], limit=1, order="id desc")
                    self.env.cr.execute("""
                        SELECT price_unit
                        FROM sale_order_line
                        WHERE state in ('sale','done') and product_id = %s and order_partner_id = %s
                        ORDER BY id DESC LIMIT 1
                    """ % (record.product_id.id, record.order_partner_id.id))
                    price_unit = self.env.cr.fetchall()
                    if price_unit:
                        price = price_unit[0][0]
                else:
                    # sale_order_line_id = self.search([('state','in',('sale','done')),('product_id', '=', record.product_id.id), ('order_id.partner_id', '=', record.order_id.partner_id.id), ('id', '!=', record.id)], limit=1, order="id desc")
                    self.env.cr.execute("""
                            SELECT price_unit
                            FROM sale_order_line
                            WHERE state in ('sale','done') and product_id = %s and order_partner_id = %s and id != %s
                            ORDER BY id DESC LIMIT 1
                        """ % (record.product_id.id, record.order_partner_id.id, record.id))
                    price_unit = self.env.cr.fetchall()
                    if price_unit:
                        price = price_unit[0][0]
                    self._cr.execute("""UPDATE sale_order_line SET last_customer_sale_price = %s WHERE product_id = %s and order_id = %s""", (price, record.product_id.id, record.order_id.id))
                    self._cr.commit()
                    list_product.append(record.product_id.id)
                    continue
                list_product.append(record.product_id.id)
            record.last_customer_sale_price = price

    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        """
        Launch procurement group run method with required/custom fields genrated by a
        sale order line. procurement group will launch '_run_pull', '_run_buy' or '_run_manufacture'
        depending on the sale order line product rule.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        if self.user_has_groups('equip3_sale_operation.group_multi_do'):
            procurements = []
            there_are_assets = False
            for line in self:
                if line.is_down_payment:
                    continue
                if line.state != 'sale' or not line.product_id.type in ('consu','product','asset'):
                    continue
                qty = line._get_qty_procurement(previous_product_uom_qty)
                if float_compare(qty, line.product_uom_qty, precision_digits=precision) >= 0:
                    continue
                group_id = line._get_procurement_group()
                if not group_id:
                    group_vals = line._prepare_procurement_group_vals()
                    group_id = self.env['procurement.group'].create(group_vals)
                line.order_id.procurement_group_id = group_id
                if not line.multiple_do_date:
                    line.multiple_do_date = line.multiple_do_date_new
                values = line._prepare_procurement_values(group_id=group_id)
                values.update({
                    'line_warehouse_id': line.line_warehouse_id.id,
                    'delivery_address_id': line.delivery_address_id.id,
                    'delivery_date': line.multiple_do_date,
                    'date_planned': line.multiple_do_date,
                    'date_deadline': line.multiple_do_date,
                    'multiple_do': True,
                    })
                product_qty = line.product_uom_qty - qty

                line_uom = line.product_uom
                quant_uom = line.product_id.uom_id
                product_qty, procurement_uom = line_uom._adjust_uom_quantities(product_qty, quant_uom)
                procurements.append(self.env['procurement.group'].Procurement(
                    line.product_id, product_qty, procurement_uom,
                    line.order_id.partner_shipping_id.property_stock_customer,
                    line.name, line.order_id.name, line.order_id.company_id, values))
                if line.product_id.type == 'asset':
                    there_are_assets = True
            if procurements:
                if there_are_assets:
                    self.env['procurement.group'].run_asset(procurements)
                else:
                    self.env['procurement.group'].run(procurements)
            return True
        else:
            temp_list = []
            line_list_vals = []
            if self:
                if not self[0].order_id.is_single_delivery_date or not self[0].order_id.is_single_warehouse:
                    for record in self:
                        if record.is_down_payment:
                            continue
                        if {'line_warehouse_id': record.line_warehouse_id.id, 'multiple_do_date_new': record.multiple_do_date_new.date(),} in temp_list:
                            filter_line = list(filter(lambda r:r.get('line_warehouse_id') == record.line_warehouse_id.id and r.get('multiple_do_date_new') == record.multiple_do_date_new.date(), line_list_vals))
                            if filter_line:
                                if record.product_id.type == 'asset':
                                    filter_line[0]['there_are_assets'] = True
                                filter_line[0]['lines'].append(record)
                        else:
                            temp_list.append({
                                'line_warehouse_id': record.line_warehouse_id.id,
                                'multiple_do_date_new': record.multiple_do_date_new.date()
                            })
                            line_list_vals.append({
                                'line_warehouse_id': record.line_warehouse_id.id,
                                'multiple_do_date_new': record.multiple_do_date_new.date(),
                                'there_are_assets': True if record.product_id.type == 'asset' else False,
                                'lines': [record]
                            })
                else:
                    self.env.cr.execute("""
                        select l.id
                        from sale_order_line as l
                        inner join product_product as p
                        on l.product_id = p.id
                        inner join product_template as pt
                        on p.product_tmpl_id = pt.id
                        where pt.type = 'asset' and l.order_id = %s
                    """ % (self[0].order_id.id))
                    is_asset = self.env.cr.fetchall()
                    if not self[0].is_down_payment:
                        line_list_vals.append({
                            'line_warehouse_id': self[0].line_warehouse_id.id,
                            'multiple_do_date_new': self[0].multiple_do_date_new.date() if self[0].multiple_do_date_new else False,
                            'there_are_assets': True if is_asset else False,
                            'lines': self
                        })
                for value in line_list_vals:
                    procurements = []
                    group_id = False
                    for line in value.get('lines'):
                        if line.state != 'sale' or not line.product_id.type in ('consu','product','asset','service'):
                            continue
                        qty = line._get_qty_procurement(previous_product_uom_qty)
                        if float_compare(qty, line.product_uom_qty, precision_digits=precision) >= 0:
                            continue
                        group_id = line._get_procurement_group()
                        if not group_id:
                            group_vals = line._prepare_procurement_group_vals()
                            group_id = self.env['procurement.group'].create(group_vals)
                        line.order_id.procurement_group_id = group_id

                        values = line._prepare_procurement_values(group_id=group_id)
                        values.update({
                            'line_warehouse_id': value.get('line_warehouse_id'),
                            'multiple_do': True,
                        })
                        product_qty = line.product_uom_qty - qty

                        line_uom = line.product_uom
                        quant_uom = line.product_id.uom_id
                        product_qty, procurement_uom = line_uom._adjust_uom_quantities(product_qty, quant_uom)
                        procurements.append(self.env['procurement.group'].Procurement(
                            line.product_id, product_qty, procurement_uom,
                            line.order_id.partner_shipping_id.property_stock_customer,
                            line.name, line.order_id.name, line.order_id.company_id, values))
                    if procurements:
                        if value.get('there_are_assets'):
                            self.env['procurement.group'].run_asset(procurements)
                        else:
                            self.env['procurement.group'].run(procurements)
            return True

    def _action_launch_stock_rule_asset(self, previous_product_uom_qty=False):
        """
        Launch procurement group run method with required/custom fields genrated by a
        sale order line. procurement group will launch '_run_pull', '_run_buy' or '_run_manufacture'
        depending on the sale order line product rule.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        procurements = []
        for line in self:
            line = line.with_company(line.company_id)
            if line.state != 'sale' or line.product_id.type != 'asset':
                continue
            qty = line._get_qty_procurement(previous_product_uom_qty)
            if float_compare(qty, line.product_uom_qty, precision_digits=precision) >= 0:
                continue

            group_id = line._get_procurement_group()
            if not group_id:
                group_id = self.env['procurement.group'].create(line._prepare_procurement_group_vals())
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
            product_qty = line.product_uom_qty - qty

            line_uom = line.product_uom
            quant_uom = line.product_id.uom_id
            product_qty, procurement_uom = line_uom._adjust_uom_quantities(product_qty, quant_uom)
            procurements.append(self.env['procurement.group'].Procurement(
                line.product_id, product_qty, procurement_uom,
                line.order_id.partner_shipping_id.property_stock_customer,
                line.product_id.display_name, line.order_id.name, line.order_id.company_id, values))
        if procurements:
            if not self.order_id.commitment_date:
                self.order_id.commitment_date = self.order_id.expected_date
            self.env['procurement.group'].run_asset(procurements)
        return True

    def _prepare_procurement_values(self, group_id=False):
        res = super(SaleOrderLine,self)._prepare_procurement_values(group_id)
        if self.line_warehouse_id.delivery_steps == 'ship_only':
            picking_type = self.env['stock.picking.type'].search([('default_location_src_id', '=', self.line_warehouse_id.default_delivery_location_id.id),
                                                                ('code', '=', 'outgoing'),
                                                                ('sequence_code', '=', 'OUT')], limit=1)
            if picking_type:
                res.update({'picking_type_id': picking_type.id})

        res.update({
            'branch_id':self.order_id.branch_id and self.order_id.branch_id.id or False,
            'location_id': self.line_warehouse_id.default_delivery_location_id.id,
        })
        if not self.order_id.is_single_warehouse:
            res.update({'warehouse_id': self.line_warehouse_id})
        return res


class SaleOrderTemplate(models.Model):
    _inherit = 'sale.order.template'


    def domain_company(self):
        return [('id', 'in', self.env.companies.ids)]

    company_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company, domain=domain_company)
    customer_ids = fields.Many2many('res.partner', 'order_template_partner_rel','partner_id', 'template_id', string="Customer")

# move to izi_sale_channel modul
# class SaleChannel(models.Model):
#     _inherit = 'sale.channel'

    # def domain_company(self):
    #     return [('id', 'in', self.env.companies.ids)]

    # company_id = fields.Many2one('res.company', string='Company', domain=domain_company)

class UoM(models.Model):
    _inherit = 'uom.uom'

    is_external_link = fields.Boolean('Is External Link', default=False)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        res = super(UoM, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                     submenu=submenu)
        is_external_link = self.env.context.get("default_is_external_link")
        doc = etree.XML(res['arch'])
        if is_external_link and view_type == 'form':
            for node in doc.xpath("//field"):
                modifiers = simplejson.loads(node.get("modifiers"))
                modifiers['readonly'] = True
                node.set('modifiers', simplejson.dumps(modifiers))
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

class ResBranch(models.Model):
    _inherit = 'res.branch'

    is_external_link = fields.Boolean('Is External Link', default=False)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        res = super(ResBranch, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                            submenu=submenu)
        is_external_link = self.env.context.get("default_is_external_link")
        doc = etree.XML(res['arch'])
        if is_external_link and view_type == 'form':
            for node in doc.xpath("//field"):
                modifiers = simplejson.loads(node.get("modifiers"))
                modifiers['readonly'] = True
                node.set('modifiers', simplejson.dumps(modifiers))
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_external_link = fields.Boolean('Is External Link', default=False)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        res = super(ResPartner, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                            submenu=submenu)
        is_external_link = self.env.context.get("default_is_external_link")
        doc = etree.XML(res['arch'])
        if is_external_link and view_type == 'form':
            for node in doc.xpath("//field"):
                modifiers = simplejson.loads(node.get("modifiers"))
                modifiers['readonly'] = True
                node.set('modifiers', simplejson.dumps(modifiers))
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

class SaleOrder(models.Model):
    _inherit = 'sale.order'



    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else False

    # @api.model
    # def _domain_branch(self):
    #     return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one(
        'res.branch',
        check_company=True,
        default = _default_branch,
        readonly=False)
    order_line_count = fields.Integer(string="Order Line", compute='order_line_calc', store=True, tracking=True)
    date_order = fields.Datetime(default=fields.Datetime.now, tracking=True)
    validity_date = fields.Date(string='Expiration', readonly=True, copy=False,tracking=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},)
    payment_term_id = fields.Many2one(
    'account.payment.term', string='Payment Terms', check_company=True,  tracking=True , # Unrequired company
    domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",)
    sale_order_template_id = fields.Many2one(
        'sale.order.template', 'Quotation Template',
        readonly=True, check_company=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        domain="['|',('customer_ids','=', False), ('customer_ids','in', partner_id)]",tracking=True)
    sale_state = fields.Selection([
                        ('pending', 'Pending'),
                        ('in_progress', 'In Progress'),
                        ('done', 'Done'),
                        ('cancel', 'Cancelled')
                ], string="Sale State", tracking=True)
    delivered_state = fields.Selection([
        ('pending', 'Pending Delivery'),
        ('partially', 'Partially Delivered'),
        ('fully', 'Fully Delivered')
    ], string="Delivered State",store=False, compute='_compute_delivery')
    # ('partially', 'Partially Delivery'),
    # ('fully', 'Fully Delivery')
    state = fields.Selection(selection_add=[
            ('waiting_for_over_limit_approval', 'Waiting For Over Limit Approval'),
            ('waiting_for_approval', 'Waiting For Sale Order Approval'),
            ('quotation_approved', 'Quotation Approved'),
            ('reject', 'Quotation Rejected'),
            ('revised', 'Order Revised'),
            ('sent','Quotation Sent')
            ])
    sale_state_1 = fields.Selection(related='sale_state')
    state_2 = fields.Selection(related='state')
    revised_state = fields.Selection(related='state')
    approval_matrix_state = fields.Selection(related='state')
    approval_matrix_state_1 = fields.Selection(related='state')
    # branch_id = fields.Many2one('res.branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)], required=True)
    account_tag = fields.Many2one('account.analytic.tag', string="Account Analytic Group")
    def _domain_analytic_group(self):
        return [('company_id','=',self.env.company.id)]
    account_tag_ids = fields.Many2many('account.analytic.tag', 'account_analytic_tag_order_rel', 'sale_id', 'tag_id', string="Analytic Group",domain=_domain_analytic_group, tracking=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")
    approving_matrix_sale_id = fields.Many2many('approval.matrix.sale.order', string="Sale Order Approval Matrix", compute='_compute_approving_customer_matrix', store=True, copy=False)
    approved_matrix_ids = fields.One2many('approval.matrix.sale.order.lines', 'order_id', string="Approved Matrix", copy=False)
    is_customer_approval_matrix = fields.Boolean(string="Custome Matrix", store=False, compute='_compute_is_customer_approval_matrix')
    hide_proforma = fields.Boolean(string="Customer Limit Approval Matrix", store=False, compute='_compute_is_customer_approval_matrix')
    is_approval_matrix_filled = fields.Boolean(string="Custome Matrix", store=False, compute='_compute_approval_matrix_filled')
    is_approve_button = fields.Boolean(string='Is Approve Button', compute='_get_approve_button', store=False)
    approval_matrix_line_id = fields.Many2one('approval.matrix.sale.order.lines', string='Sale Approval Matrix Line', compute='_get_approve_button', store=False)
    is_quotation_cancel = fields.Boolean(string='Is Quotation Cancel', default=False)

    company_id = fields.Many2one(readonly=True)
    deduction_ids = fields.One2many('sale.order.deduction', 'sale_id', string='Deduction Lines')
    analytic_accounting = fields.Boolean("Analyic Account", compute="get_analytic_accounting", store=True)
    terms_conditions_id = fields.Many2one('sale.terms.and.conditions', string='Terms and Conditions', tracking=True)
    group_multi_do = fields.Boolean(string="Multiple Delivery Address?", compute='_compute_group_multi_do', store=False)
    is_single_warehouse = fields.Boolean(string="Single Warehouse", default=True, tracking=True)
    is_single_delivery_date = fields.Boolean(string="Single Delivery Date", default=True, tracking=True)
    commitment_date = fields.Datetime('Delivery Date', copy=False, default=fields.Datetime.now, tracking=True,
                                      states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
                                      help="This is the delivery date promised to the customer. "
                                           "If set, the delivery order will be scheduled based on "
                                           "this date rather than product lead times.")
    revised_sale_order_ids = fields.Many2many('sale.order', 'sale_order_revision_rel', 'sale_id', 'revision_id', string="Revised Sale Order")
    revised_sale_order_id = fields.Many2one('sale.order', string="Revised Sale Order")
    is_revision_so = fields.Boolean(string='Is Revision SO')
    is_print_report = fields.Boolean(string="Is Print Reports", store=False, compute='_compute_is_print_report')
    qty_delivered = fields.Integer("Delivery Qty", store=False, compute='_compute_delivery')
    count_delivered = fields.Integer("Delivery Count", store=False, compute='_compute_delivery')
    multilevel_disc = fields.Boolean(string="Multi Level Discount", compute="")
    multi_discount = fields.Char('Multi Discount')
    discount_method = fields.Selection([('fix', 'Fixed'), ('per', 'Percentage')], 'Discount Method', default='fix', tracking=True)
    discount_amount = fields.Float('Discount Amount', tracking=True)
    date_confirm = fields.Datetime(string='Confirm Date', readonly=True, copy=False, help="Confirmation date of confirmed orders.")
    is_sale_order = fields.Boolean(string="Is Sale Order", default=True, compute='_compute_is_sale_order')
    partner_name = fields.Char(related='partner_id.name', readonly=True, store=True)
    is_hidden_button = fields.Boolean(compute='_compute_is_hidden_button', string="Is Hidden Button")
    lock_sale_order = fields.Boolean(compute='_compute_lock_sale_order',string='Lock Sale Order in Quotation')
    readonly_disc = fields.Boolean(string='Readonly Disc', compute='_compute_readonly_disc', store=True)
    readonly_multi = fields.Boolean(string='Readonly Multi', compute='_compute_readonly_disc', store=True)
    brand = fields.Many2one('product.brand', string="Brand")
    partner_invoice_id = fields.Many2one(
        'res.partner', string='Invoice Address', tracking=True,
        readonly=True, required=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'sale': [('readonly', False)], 'quotation_approved': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",)
    partner_shipping_id = fields.Many2one(
        'res.partner', string='Delivery Address', readonly=True, required=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'sale': [('readonly', False)], 'quotation_approved': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",)

    reject_reason = fields.Char(string='Reason Rejected')

    sale_fully_delivered = fields.Boolean(
        string="Fully Delivered", readonly=True, default=False)
    sale_partially_delivery = fields.Boolean(
        string="Partially Delivered", readonly=True, default=False)
    sale_fully_paid = fields.Boolean(
        string="Fully Paid", readonly=True, default=False)
    sale_partially_paid = fields.Boolean(
        string="Partially Paid", readonly=True, default=False)
    sale_hidden_compute_field = fields.Boolean(
        string="Hidden Compute Shipment", readonly=True, compute="_compute_shipment")

    date_kanban = fields.Char(compute="_compute_date_kanban", readonly=True)
    is_down_payment = fields.Boolean(string='Is Down Payment Invoice')
    down_payment_amount = fields.Float(string='Down Payment', compute='_compute_down_payment_amount', store=True)
    down_payment_amount_percentage = fields.Float(string='Down Payment (%)', compute='_compute_down_payment_amount', store=True)
    tax_down_payment_amount = fields.Float(string='Tax Down Payment', compute='_compute_down_payment_amount', store=True)
    total_amount_without_dp = fields.Float(string='Total', compute='_amount_all', store=True)
    # remove or add tracking value
    carrier_id = fields.Many2one('delivery.carrier', string="Delivery Method", domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", help="Fill this field if you plan to invoice the shipping based on picking.", tracking=True)
    amount_untaxed = fields.Monetary(string='Total Untaxed Amount', store=True, readonly=True, compute='_amount_all')
    amount_tax = fields.Monetary(string='Total Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Grand Total', store=True, readonly=True, compute='_amount_all')
    order_line = fields.One2many(
        'sale.order.line', 'order_id', string='Order Lines',
        states={'cancel': [('readonly', True)], 'done': [('readonly', True)]},
        copy=True, auto_join=True, tracking=True)
    discount_type = fields.Selection([('line', 'Order Line'), ('global', 'Global')],string='Discount Applies to',default='global', tracking=True)
    city_id = fields.Many2one('res.country.city', 'City', related='partner_id.res_city_id', store=True)
    state_id = fields.Many2one('res.country.state', string='States', related='partner_id.state_id', store=True)
    show_mobile = fields.Boolean("Show Mobile", compute="")
    is_external_link = fields.Boolean('Is External Link', default=False)
    tax_discount_policy = fields.Selection([('untax', 'After Discount'), ('tax', 'Before Discount')],
                                           string='Tax Applies on')
    discount_amt_before = fields.Monetary(string='- Discount', digits='Discount', readonly=True)
    discount_amt_line_before = fields.Monetary(string='- Line Discount', digits='Line Discount', readonly=True)
    amount_subtotal = fields.Monetary(compute='_amount_all', string='Subtotal', store=True, readonly=True)
    recurring_invoices = fields.Boolean("Recurring Invoices", compute='_compute_recurring_invoices', store=True)
    is_with_dp = fields.Boolean("With Down Payment")
    down_payment_amount_recurring = fields.Float("Down Payment", default=1.0)
    down_payment_type_recurring = fields.Selection([('fixed', 'Fixed'), ('percentage', 'Percentage')],
                                         string='Type', default='fixed')
    recurring_period = fields.Integer("Recurring Period", default=1)
    recurring_type = fields.Selection([('week', 'Week(s)'), ('month', 'Month(s)'), ('year', 'Year(s)')],
                                      string='Type', default='month')
    total_recurring = fields.Integer("Total Recurring", default=3)
    invoicing_policy = fields.Selection([('order', 'Ordered Quantities'), ('deliver', 'Delivered Quantities')],
                                        string='Invoicing Policy', default='order')
    first_invoice_date = fields.Date("Date of First Invoice", default=fields.Date.today)
    recurring_invoice_ids = fields.One2many('recurring.invoices','sale_id', string="Recurring Invoices")
    dp_amount_recurring = fields.Float("DP")
    amount_total_recurring = fields.Float("Amount Total Recurring")
    total_recurring_per_line = fields.Float("Total Recurring per Line")
    diff = fields.Float("Diff amount total")
    next_invoice_date = fields.Date('Next Invoice Date', copy=False)
    total_invoice = fields.Integer("Total Invoice")
    invoice_recurring_created = fields.Integer("Invoice Created", copy=False)
    done_recurring = fields.Boolean("Done", copy=False)
    product_delivered = fields.Many2many('product.template','list_product_delivered_rel', 'order_id', 'product_id' ,string='Product Delivered')
    hide_button_qa_sale = fields.Html(string='Hide Button', sanitize=False, compute='_compute_hide_button', store=True)
    filter_delivery_address_id = fields.Char("Partner Address", compute='_compute_partner_address', store=True)
    filter_branch = fields.Char(string="Filter Branch", compute='_compute_filter_branch', store=False)
    is_backorder = fields.Boolean("Backorder")

    def update_prices(self):
        self.env.context = dict(self._context)
        self.env.context.update({'order_line': True})
        res = super().update_prices()
        return res

    def _create_invoices(self, grouped=False, final=False, date=None):
        res = super()._create_invoices(grouped, final, date)
        res._onchange_analytic_group()
        return res
    
    @api.depends('company_id', 'branch_id')
    def _compute_allowed_customers(self):
        for rec in self:
            IrConfigParam = self.env['ir.config_parameter'].sudo()
            approval = IrConfigParam.get_param('is_customer_partner_approval_matrix')
            rec.allowed_customer_ids = json.dumps([])
            if approval:
                rec.allowed_customer_ids = json.dumps([
                                                       ('state_customer', '=', 'approved'),
                                                       ('is_customer', '=', True), 
                                                       ('customer_rank', '>', 0), 
                                                       ])
            else:
                rec.allowed_customer_ids = json.dumps([
                                                       ('state_customer', '=', 'approved'),
                                                       ('is_customer', '=', True), 
                                                       ('customer_rank', '>', 0)
                                                       ])
                
    allowed_customer_ids = fields.Char('res.partner', compute=_compute_allowed_customers)

    
    @api.depends('company_id')
    def _compute_filter_branch(self):
        for rec in self:
            rec.filter_branch = json.dumps(
                [('id', 'in', self.env.branches.ids), ('company_id', '=', self.company_id.id)])

    @api.onchange('user_id')
    def onchange_user_id(self):
        super().onchange_user_id()
        if self.state in ['draft','sent']:
            self.warehouse_id = self.warehouse_new_id.id

    @api.depends('partner_id','group_multi_do')
    def _compute_partner_address(self):
        for record in self:
            if self.user_has_groups('equip3_sale_operation.group_multi_do'):
                partner_ids = record.partner_id.child_ids.filtered(lambda r: r.type == 'delivery')
                if record.partner_id and record.partner_id.child_ids and partner_ids:
                    record.filter_delivery_address_id = json.dumps([('id', 'in', partner_ids.ids)])
                else:
                    record.filter_delivery_address_id = json.dumps([('id', 'in', record.partner_id.ids)])
            else:
                record.filter_delivery_address_id = json.dumps([('id', 'in', [])])

    @api.depends('state')
    def _compute_hide_button(self):
        for rec in self:
            if rec.state in ('sale', 'quotation_approved'):
                rec.hide_button_qa_sale = '<style>.o_field_x2many_list_row_add, .fa.fa-trash-o {display: none !important;}</style>'
            else:
                rec.hide_button_qa_sale = False

    @api.depends('state', 'order_line.invoice_status')
    def _get_invoice_status(self):
        """
        Compute the invoice status of a SO. Possible statuses:
        - no: if the SO is not in status 'sale' or 'done', we consider that there is nothing to
          invoice. This is also the default value if the conditions of no other status is met.
        - to invoice: if any SO line is 'to invoice', the whole SO is 'to invoice'
        - invoiced: if all SO lines are invoiced, the SO is invoiced.
        - upselling: if all SO lines are invoiced or upselling, the status is upselling.
        """
        rec = self.filtered(lambda so: so.recurring_invoices == False)
        if rec:
            return super()._get_invoice_status()
        else:
            unconfirmed_orders = self.filtered(lambda so: so.state not in ['sale', 'done'])
            unconfirmed_orders.invoice_status = 'no'
            confirmed_orders = self - unconfirmed_orders
            if not confirmed_orders:
                return
            line_invoice_status_all = [
                (d['order_id'][0], d['invoice_status'])
                for d in self.env['sale.order.line'].read_group([
                    ('order_id', 'in', confirmed_orders.ids),
                    ('is_downpayment', '=', False),
                    ('is_recurring','=', False),
                    ('display_type', '=', False),
                ],
                    ['order_id', 'invoice_status'],
                    ['order_id', 'invoice_status'], lazy=False)]
            for order in confirmed_orders:
                line_invoice_status = [d[1] for d in line_invoice_status_all if d[0] == order.id]
                if order.state not in ('sale', 'done'):
                    order.invoice_status = 'no'
                elif any(invoice_status == 'to invoice' for invoice_status in line_invoice_status):
                    order.invoice_status = 'to invoice'
                elif line_invoice_status and all(invoice_status == 'invoiced' for invoice_status in line_invoice_status):
                    order.invoice_status = 'invoiced'
                elif line_invoice_status and all(invoice_status in ('invoiced', 'upselling') for invoice_status in line_invoice_status):
                    order.invoice_status = 'upselling'
                else:
                    order.invoice_status = 'no'


    @api.depends('order_line.is_recurring','order_line')
    def _compute_recurring_invoices(self):
        for rec in self:
            is_recurring = False
            if rec.order_line:
                is_recurring = True if rec.order_line.filtered(lambda x: x.is_recurring) else False
            rec.recurring_invoices = is_recurring

    def _action_sale_order_create_inv_recurring(self):
        today = fields.Date.today()
        self.env.cr.execute("""
            SELECT id
            FROM sale_order
            WHERE recurring_invoices = True AND done_recurring = False AND next_invoice_date = '%s'""" % (today.strftime("%Y%m%d")))
        order_ids = self.env.cr.dictfetchall()
        order_ids = list(map(itemgetter('id'), order_ids))
        order_ids = self.env['sale.order'].browse(order_ids)
        self.create_invoice_recurring(order_ids)

    def create_invoice_recurring(self, order_ids):
        for rec in order_ids:
            # total = 0
            # payment = rec.create_sale_advance_payment_inv('delivered', 0)
            if rec.invoice_recurring_created != rec.total_invoice:
                # payment.with_context(is_recurring=True).create_invoices()
                rec.with_context(is_recurring=True)._create_invoices(grouped=False, final=False)
                rec.next_invoice_date = rec.get_invoice_recurring_date(rec.next_invoice_date or date.today())
                simulation_recurring = rec.recurring_invoice_ids.filtered(lambda x:not x.invoice_id)
                if simulation_recurring:
                    simulation_recurring[0].invoice_id = rec.invoice_ids[-1].id
                rec.invoice_recurring_created += 1

    @api.onchange('invoicing_policy')
    def set_first_invoice_date(self):
        for rec in self:
            if rec.invoicing_policy == 'deliver':
                rec.first_invoice_date = False

    def create_simulation_recurring(self):
        for rec in self:
            seq = 1
            first_invoice_date = next_invoice_date = rec.first_invoice_date or date.today()
            total = sum(rec.order_line.filtered(lambda x: x.is_recurring).mapped('price_total'))
            for i in range(rec.total_recurring):
                self.env['recurring.invoices'].create({
                    'sale_id': rec.id,
                    'sequence': i+1,
                    'invoice_date': first_invoice_date if i == 0 else next_invoice_date,
                    'total': total
                })
                next_invoice_date = rec.get_invoice_recurring_date(next_invoice_date)

    def create_recurring_inv_sale(self):
        for rec in self:
            if rec.recurring_invoices and not rec.done_recurring:
                rec.done_recurring = False #di db suka null
                rec.set_date_recurring_invoices()
                if rec.invoicing_policy == 'order':
                    rec.create_simulation_recurring()
                rec.next_invoice_date = rec.first_invoice_date

                if rec.first_invoice_date == date.today():
                    rec.create_invoice_recurring(self)

    def action_confirm(self):
        self.env.context = dict(self._context)
        self.env.context.update({'from_action_confirm': True})
        self.update_invoice_policy()
        res = super().action_confirm()
        for rec in self:
            rec.create_recurring_inv_sale()
        return res
    
    def update_invoice_policy(self):
        is_product_service_operation_delivery = self.env['ir.config_parameter'].sudo().get_param('is_product_service_operation_delivery', False)
        if not is_product_service_operation_delivery:
            query = """
                    UPDATE product_template
                    SET invoice_policy = 'order'
                    WHERE id IN (
                        SELECT pt.id
                        FROM product_template AS pt
                        JOIN product_product AS pp ON pt.id = pp.product_tmpl_id
                        JOIN sale_order_line AS sol ON pp.id = sol.product_id
                        WHERE pt.invoice_policy = 'delivery'
                        AND pt.type = 'service'
                    )
                """
            self.env.cr.execute(query)
            self.env.cr.commit()

    def set_date_recurring_invoices(self):
        for rec in self:
            if rec.invoicing_policy == 'order':
                if rec.date_confirm.date() > rec.first_invoice_date:
                    rec.first_invoice_date = rec.date_confirm.date()
            rec.total_invoice = rec.total_recurring

    def create_sale_advance_payment_inv(self, advance_payment_method, amount):
        payment = self.env['sale.advance.payment.inv'].with_context({
            'active_model': 'sale.order',
            'active_ids': self.ids,
            'active_id': self.id,
            'default_journal_id': self.env['account.journal'].sudo().search([('type', '=', 'sale'),('company_id','=',self.company_id.id)], limit=1).id,
        }).create({
            'advance_payment_method': 'delivered'
        })
        return payment

    def get_invoice_recurring_date(self,date):
        for rec in self:
            if rec.recurring_type == 'week':
                return date + relativedelta(weeks=rec.recurring_period)
            elif rec.recurring_type == 'month':
                return date + relativedelta(months=rec.recurring_period)
            elif rec.recurring_type == 'year':
                return date + relativedelta(years=rec.recurring_period)



    @api.onchange('down_payment_amount_recurring')
    def check_down_payment_recurring(self):
        for rec in self:
            if rec.is_with_dp and rec.down_payment_amount_recurring < 1:
                raise ValidationError("Down Payment must be greater than 0.")

    @api.onchange('recurring_period')
    def check_recurring_period(self):
        for rec in self:
            if rec.recurring_period < 1:
                raise ValidationError("Recurring period must be greater than 0.")

    @api.onchange('total_recurring')
    def check_total_recurring(self):
        for rec in self:
            if rec.total_recurring < 1:
                raise ValidationError("Total Recurring must be greater than 0.")

    @api.model
    def default_sh_sale_bm_is_cont_scan(self):
        return self.env.company.sh_sale_bm_is_cont_scan

    sh_sale_bm_is_cont_scan = fields.Char(
        string='Continuously Scan?', default=default_sh_sale_bm_is_cont_scan, readonly=False)

    continuously_scan_setting = fields.Boolean("Setting Continuously Scan", compute='', store=True)

    # @api.depends('company_id')
    # def _compute_continuously_scan_setting(self):
    #     for rec in self:
    #         rec.continuously_scan_setting = self.env.company.sh_sale_bm_is_cont_scan

    def _website_product_id_change(self, order_id, product_id, qty=0):
        res = super(SaleOrder, self)._website_product_id_change(order_id, product_id, qty=qty)
        order = self.sudo().browse(order_id)
        commitment_date = order.commitment_date
        res.update({
            'multiple_do_date': commitment_date,
            'multiple_do_date_new': commitment_date,
        })
        return res

    def _get_invoiceable_lines(self, final=False):
        """Return the invoiceable lines for order `self`."""
        inv_dp = self.invoice_ids.filtered(lambda x: x.is_dp == True)
        if not inv_dp and not 'is_recurring' in self.env.context:
            order_lines = super()._get_invoiceable_lines(final)
            return order_lines.filtered(lambda o: not o.is_recurring)
        else:
            down_payment_line_ids = []
            invoiceable_line_ids = []
            pending_section = None
            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

            for line in self.order_line:
                if line.display_type == 'line_section':
                    # Only invoice the section if one of its lines is invoiceable
                    pending_section = line
                    continue
                if final:
                    if line.is_downpayment:
                        # Keep down payment lines separately, to put them together
                        # at the end of the invoice, in a specific dedicated section.
                        down_payment_line_ids.append(line.id)
                        continue
                    if pending_section:
                        invoiceable_line_ids.append(pending_section.id)
                        pending_section = None
                    invoiceable_line_ids.append(line.id)
                if 'is_recurring' in self.env.context:
                    if not line.is_downpayment and line.is_recurring:
                        invoiceable_line_ids.append(line.id)
                    # else:
                    #     down_payment_line_ids.append(line.id)
            return self.env['sale.order.line'].browse(invoiceable_line_ids + down_payment_line_ids)

    # @api.model
    # def _prepare_down_payment_section_line(self, **optional_values):
    #     line_dp_id = self.order_line.filtered(lambda x: x.is_down_payment == True)
    #     res = super()._prepare_down_payment_section_line(**optional_values)
    #     if line_dp_id:
    #         res['display_type'] = line_dp_id.display_type
    #         res['product_id'] = line_dp_id.product_id.id
    #         res['product_uom_id'] = line_dp_id.product_uom.id
    #         res['quantity'] = line_dp_id.product_uom_qty
    #         res['price_unit'] = line_dp_id.price_unit
    #         res['is_down_payment'] = line_dp_id.is_down_payment
    #     return res

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        res = super(SaleOrder, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                     submenu=submenu)
        is_external_link = self.env.context.get("default_is_external_link")
        doc = etree.XML(res['arch'])
        if view_type == 'form':
            for node in doc.xpath("//field"):
                modifiers = simplejson.loads(node.get("modifiers"))
                if is_external_link:
                    modifiers['readonly'] = True
                else:
                    if 'readonly' not in modifiers:
                        modifiers['readonly'] = [['state','=','done']]
                    else:
                        if type(modifiers['readonly']) != bool:
                            add_new = True
                            for i in modifiers['readonly']:
                                if 'state' in i:
                                    add_new = False
                                    if i[1] == '=':
                                        i[1] = 'in'
                                        i[2] = (i[2], 'done')
                                    elif i[1] == 'in':
                                        i[2].append('done')
                            if add_new:
                                modifiers['readonly'].insert(0, '|')
                                modifiers['readonly'] += [['state','=','done']]
                            
                node.set('modifiers', simplejson.dumps(modifiers))
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

    # @api.depends('company_id')
    # def _compute_show_mobile(self):
    #     for rec in self:
    #         rec.show_mobile = self.env['ir.config_parameter'].sudo().get_param('show_sale_barcode_mobile_type')

    @api.model
    def _default_warehouse_id(self):
        # !!! Any change to the default value may have to be repercuted
        # on _init_column() below.
        res = super()._default_warehouse_id()
        res = False
        return res

    @api.onchange('branch_id','company_id')
    def set_warehouse_id(self):
        for res in self:
            if res.branch_id and res.company_id:
                stock_warehouse = res.env['stock.warehouse'].search([('company_id', '=', res.company_id.id),('branch_id', '=', res.branch_id.id),('id','in',self.env.user.warehouse_ids.ids)], order="id", limit=1)
                res.warehouse_id = stock_warehouse or False
                res.warehouse_new_id = stock_warehouse or False
            else:
                res.warehouse_id = False
                res.warehouse_new_id = False

    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse',
        required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        default=False, tracking=True)

    warehouse_new_id = fields.Many2one(
        'stock.warehouse', string='New Warehouse', required=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    filter_destination_warehouse = fields.Char(string="Filter Destination Warehouse",compute='_compute_filter_destination', store=False)

    @api.depends('company_id','branch_id')
    def _compute_filter_destination(self):
        for rec in self:
            if rec.branch_id:
                rec.filter_destination_warehouse = json.dumps([('branch_id', '=', rec.branch_id.id), ('company_id', '=', rec.company_id.id),('id','in',self.env.user.warehouse_ids.ids)])
            else:
                rec.filter_destination_warehouse = json.dumps([('id', 'in', 0)])

    @api.onchange('warehouse_new_id')
    def set_value_warehouse_id(self):
        for rec in self:
            rec.warehouse_id = rec.warehouse_new_id

    @api.depends('order_line', 'order_line.is_down_payment', 'order_line.price_unit', 'order_line.price_tax')
    def _compute_down_payment_amount(self):
        for record in self:
            dp_ids = record.order_line.filtered(lambda r: r.is_down_payment)
            down_payment_amount = sum(dp_ids.mapped('price_unit'))
            tax_dp = sum(dp_ids.mapped('price_tax'))
            type_tax = dp_ids[0].tax_id.amount_type if dp_ids else ''
            record.down_payment_amount = down_payment_amount - tax_dp if type_tax == 'division' else down_payment_amount
            record.down_payment_amount_percentage = (record.down_payment_amount / record.amount_total) * 100 if record.amount_total else 100
            record.tax_down_payment_amount = tax_dp

    @api.depends('date_order')
    def _compute_date_kanban(self):
        for rec in self:
            ts = rec.date_order.timestamp()
            dt = datetime.fromtimestamp(ts, pytz.timezone('Asia/Jakarta'))
            rec.write({'date_kanban': dt.strftime("%m/%d/%Y - %H:%M:%S")})

    @api.depends("order_line.qty_delivered")
    def _compute_shipment(self):
        for rec in self:
            rec.sale_hidden_compute_field = True
            if rec.state in ('sale','done'):
                rec.sale_hidden_compute_field = False
                # rec.write({'sale_hidden_compute_field':False})
                if 'compute_shipment' not in self.env.context:
                    sale_fully_delivered = False
                    sale_partially_delivery = False
                    sale_fully_paid = False
                    sale_partially_paid = False
                    if rec.delivered_state and not rec.sale_hidden_compute_field:
                        if rec.delivered_state == 'fully':
                            sale_fully_delivered = True
                        elif rec.delivered_state == 'partially' :
                            sale_partially_delivery = True
                    if rec.invoice_ids and not rec.sale_hidden_compute_field:
                        sum_of_invoice_paid = 0
                        for invoice_id in rec.invoice_ids.filtered(lambda inv: inv.state not in ['cancel', 'draft']):
                            if invoice_id.payment_state == 'paid':
                                sum_of_invoice_paid += 1
                        if sum_of_invoice_paid != 0:
                            if sum_of_invoice_paid < len(rec.invoice_ids):
                                sale_partially_paid = True
                            else:
                                sale_fully_paid = True
                    if sale_fully_paid or sale_partially_paid or sale_fully_delivered or sale_partially_delivery:
                        rec.write({
                            'sale_fully_paid': sale_fully_paid,
                            'sale_partially_paid': sale_partially_paid,
                            'sale_fully_delivered': sale_fully_delivered,
                            'sale_partially_delivery': sale_partially_delivery,
                        })
        self.env.context = dict(self._context)
        self.env.context.update({'compute_shipment': True})


    def _prepare_invoice(self):
        res = super(SaleOrder,self)._prepare_invoice()
        res.update({
            'branch_id': self.branch_id.id,
            'invoice_user_id': self.user_id and self.user_id.id or False
        })
        if 'is_recurring' in self.env.context:
            res['is_recurring'] = True
        return res

    def action_send_message_wa_mass(self):
        message = []
        for rec in self:
            created_message = rec.env['acrux.chat.message.wizard'].with_context({
                'default_partner_id': rec.partner_id.id,
                'custom_model': 'sale.order',
                'sale_id': rec.id,
            }).create({}).id
            message.append(created_message)
        return {
            'name': 'Send Message Mass',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'send.message.mass',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': {'default_message_chat_ids': message, 'default_total_row': len(self)},
        }

    @api.depends('order_line','order_line.price_total','order_line.price_subtotal', \
                 'order_line.product_uom_qty','discount_amount', \
                 'discount_method','discount_type' ,'order_line.discount_amount', \
                 'order_line.discount_method','order_line.discount_amt','down_payment_amount','is_down_payment')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        res_config= self.env['ir.config_parameter'].sudo().search([],order="id desc", limit=1)
        cur_obj = self.env['res.currency']
        for order in self:
            order_line = order.order_line.filtered(lambda x: x.is_promotion_disc_product_line != True)
            gross_total = 0
            for line_gross in order_line:
                if not line_gross.is_down_payment:
                    gross_total += line_gross.product_uom_qty * line_gross.price_unit

            for line in order_line:
                if not line.is_down_payment:
                    if order.discount_type == 'global':
                        discount_amount = 0
                        if order.discount_method == 'fix':
                            if gross_total > 0:
                                discount_amount = (order.discount_amount / gross_total) * (
                                        line.product_uom_qty * line.price_unit)
                        else:
                            discount_amount = order.discount_amount

                        line.update({
                            'discount_method': order.discount_method,
                            'discount_amount': discount_amount
                        })

            applied_discount = line_discount = sums = order_discount =  amount_untaxed = amount_taxed = amount_tax = amount_after_discount =  0.0
            subtotal = discounted_value = 0
            disc_promo = 0
            tax_discount_policy = order.tax_discount_policy
            for line in order.order_line:
                if not line.is_promotion_disc_product_line:
                    amount_untaxed += line.price_subtotal if not line.is_down_payment else 0
                    amount_taxed += line.price_total
                    amount_tax += line.price_tax if not line.is_down_payment else 0
                    applied_discount += line.discount_amt
                    discounted_value += line.discounted_value
                    subtotal += line.product_uom_qty * line.price_unit if not line.is_down_payment else 0

                    if line.discount_method == 'fix':
                        line_discount += line.discount_amount if not line.is_down_payment else 0
                    elif line.discount_method == 'per':
                        line_discount += line.price_subtotal * (line.discount_amount/ 100) if not line.is_down_payment else 0
                else:
                    discounted_value += abs(line.price_total)
                    line_discount += abs(line.price_total)
                    disc_promo += abs(line.price_total)
            order.amount_subtotal = subtotal if tax_discount_policy == 'tax' else amount_untaxed + line_discount

            if res_config:
                # tax_discount_policy = self.env.company.tax_discount_policy or False
                if tax_discount_policy == 'tax':
                    if order.discount_type == 'line':
                        order.discount_amt = 0.00
                        # order.discount_amt_before = 0.00
                        order.write({
                            'amount_untaxed': amount_untaxed,
                            'amount_tax': amount_tax,
                            'amount_total': amount_untaxed + amount_tax - discounted_value, # - line_discount
                            'discount_amt_line': line_discount,
                            # 'discount_amt_line_before' : line_discount,
                        })

                    elif order.discount_type == 'global':
                        order.discount_amt_line = 0.00
                        # order.discount_amt_line_before = 0.00

                        if order.discount_method == 'per':
                            order_discount = (amount_untaxed+amount_tax) * (order.discount_amount / 100)
                            order.write({
                                'amount_untaxed': amount_untaxed,
                                'amount_tax': amount_tax,
                                'amount_total': amount_untaxed + amount_tax - order_discount - disc_promo,
                                'discount_amt': order_discount + disc_promo,
                                # 'discount_amt_before' : order_discount,
                            })
                        elif order.discount_method == 'fix':
                            order_discount = order.discount_amount
                            order.write({
                                'amount_untaxed': amount_untaxed,
                                'amount_tax': amount_tax,
                                'amount_total': amount_untaxed + amount_tax - order_discount - disc_promo,
                                'discount_amt': order_discount + disc_promo,
                                # 'discount_amt_before' : order_discount,
                            })
                        else:
                            order.write({
                                'amount_untaxed': amount_untaxed,
                                'amount_tax': amount_tax,
                                'amount_total': amount_untaxed + amount_tax - disc_promo,
                            })
                    else:
                        order.write({
                            'amount_untaxed': amount_untaxed,
                            'amount_tax': amount_tax,
                            'amount_total': amount_untaxed + amount_tax - disc_promo,
                        })
                elif tax_discount_policy == 'untax':
                    # amount_untaxed = order.currency_id.round(sum(order.order_line.mapped('price_subtotal'))) + order.currency_id.round(sum(order.order_line.mapped('discounted_value')))
                    amount_taxed = amount_untaxed + order.currency_id.round(sum(order.order_line.filtered(lambda x: not x.is_down_payment).mapped('price_tax')))
                    if order.discount_type == 'line':
                        order.discount_amt = 0.00
                        # order.discount_amt_before = 0.00
                        order.write({
                            'amount_untaxed': amount_untaxed - disc_promo,
                            'amount_tax': amount_tax,
                            'amount_total': amount_taxed - disc_promo, # - applied_discount,
                            'discount_amt_line': applied_discount + disc_promo,
                            'amount_subtotal': amount_untaxed + applied_discount
                            # 'discount_amt_line_before' : applied_discount,
                        })
                    elif order.discount_type == 'global':
                        order.discount_amt_line = 0.00
                        # order.discount_amt_line_before = 0.00
                        if order.discount_method == 'per':
                            # order_discount = amount_untaxed * (order.discount_amount / 100)
                            order_discount = 0
                            if order.order_line:
                                for line in order.order_line:
                                    if line.tax_id:
                                        # final_discount = 0.0
                                        # try:
                                        #     final_discount = ((order.discount_amount*line.price_subtotal)/100.0)
                                        # except ZeroDivisionError:
                                        #     pass
                                        # discount = line.price_subtotal - final_discount
                                        # taxes = line.tax_id.compute_all(discount, \
                                        #                                 order.currency_id,1.0, product=line.product_id, \
                                        #                                 partner=order.partner_id)
                                        # sums += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                                        sums += line.price_tax if not line.is_down_payment and not line.is_promotion_disc_product_line else 0
                                    order_discount += line.discounted_value if not line.is_promotion_disc_product_line else 0
                            order.write({
                                'amount_untaxed': amount_untaxed - disc_promo,
                                'amount_tax': sums,
                                'amount_total': amount_taxed - disc_promo, # - order_discount,
                                'discount_amt': order_discount + disc_promo,
                                'amount_subtotal': amount_untaxed + order_discount
                                # 'discount_amt_before' : order_discount,
                            })
                        elif order.discount_method == 'fix':
                            order_discount = order.discount_amount
                            if order.order_line:
                                for line in order.order_line:
                                    if line.tax_id:
                                        # final_discount = 0.0
                                        # try:
                                        #     final_discount = ((order.discount_amount*line.price_subtotal)/amount_untaxed)
                                        # except ZeroDivisionError:
                                        #     pass
                                        # discount = line.price_subtotal - final_discount
                                        #
                                        # taxes = line.tax_id.compute_all(discount, \
                                        #                                 order.currency_id,1.0, product=line.product_id, \
                                        #                                 partner=order.partner_id)
                                        # sums += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                                        sums += line.price_tax if not line.is_down_payment and not line.is_promotion_disc_product_line else 0
                            order.write({
                                'amount_untaxed': amount_untaxed - disc_promo,
                                'amount_tax': sums,
                                'amount_total': amount_untaxed + sums - disc_promo, # - order_discount,
                                'discount_amt': order_discount + disc_promo,
                                'amount_subtotal': amount_untaxed + order_discount
                                # 'discount_amt_before' : order_discount,
                            })
                        else:
                            order.write({
                                'amount_untaxed': amount_untaxed - disc_promo,
                                'amount_tax': amount_tax,
                                'amount_total': amount_untaxed + amount_tax - disc_promo,
                            })
                    else:
                        order.write({
                            'amount_untaxed': amount_untaxed - disc_promo,
                            'amount_tax': amount_tax,
                            'amount_total': amount_untaxed + amount_tax - disc_promo,
                        })
                else:
                    order.write({
                        'amount_untaxed': amount_untaxed - disc_promo,
                        'amount_tax': amount_tax,
                        'amount_total': amount_untaxed + amount_tax - disc_promo,
                    })
            else:
                order.write({
                    'amount_untaxed': amount_untaxed - disc_promo,
                    'amount_tax': amount_tax,
                    'amount_total': amount_untaxed + amount_tax - disc_promo,
                })
            if order.is_down_payment:
                order.write({
                    'total_amount_without_dp': order.amount_total - order.down_payment_amount - order.tax_down_payment_amount
                })
            if order.amount_subtotal:
                if order.discount_type == 'global':
                    if order.amount_subtotal <= order.discount_amt:
                        raise ValidationError("Discount exceeds order subtotal.")
                elif order.discount_type == 'line':
                    if order.amount_subtotal <= order.discount_amt_line:
                        raise ValidationError("Discount exceeds order subtotal.")

    def action_quotation_send(self):
        ''' Opens a wizard to compose an email, with relevant mail template loaded by default '''
        self.ensure_one()
        template_id = self._find_mail_template()
        lang = self.env.context.get('lang')
        template = self.env['mail.template'].browse(template_id)
        if template.lang:
            lang = template._render_lang(self.ids)[self.id]
        ctx = {
            'default_model': 'sale.order',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'custom_layout': "mail.mail_notification_paynow",
            'proforma': self.env.context.get('proforma', False),
            'force_email': True,
            'model_description': self.with_context(lang=lang).type_name,
        }
        return {
            'name': 'Send Email',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    @api.model
    def _compute_is_sale_order(self):
        # import wdb; wdb.set_trace()
        string = self.name
        cari = re.search("^SO", string)
        if cari:
            self.is_sale_order = True
        else:
            self.is_sale_order = False

    @api.onchange('sale_order_template_id')
    def onchange_sale_order_template_id(self):
        res = super(SaleOrder, self).onchange_sale_order_template_id()
        if self.order_line:
            for line in self.order_line:
                line.set_account_group()
                if line.order_id.sale_order_template_id and line.order_id.commitment_date:
                    line.multiple_do_date_new = line.order_id.commitment_date
            self.set_del_add_line()
            self.set_account_group_lines()
        return res

    # @api.depends("state")
    # def _compute_multilevel_disc(self):
    #     for res in self:
    #         res.multilevel_disc = self.env['ir.config_parameter'].sudo().get_param('multilevel_disc_sale')

    def get_disocunt(self,percentage,amount):
        new_amount = (percentage * amount)/100
        return (amount - new_amount)

    @api.onchange('multi_discount')
    def _onchange_multi_discount(self):
        if self.discount_method == 'per':
            if self.multi_discount:
                amount = 100
                discount_amount = 0
                splited_discounts = self.multi_discount.split("+")
                for disocunt in splited_discounts:
                    try:
                        amount = self.get_disocunt(float(disocunt),amount)
                    except ValueError:
                        raise ValidationError("Please Enter Valid Multi Discount")
                discount_amount = 100 - amount
                if 0 < discount_amount < 100:
                    self.discount_amount = discount_amount
                else:
                    raise ValidationError("Please Enter Valid Multi Discount")
            else:
                self.discount_amount = 0

    @api.onchange('discount_type')
    def reset_disc(self):
        for rec in self:
            rec.set_disc_value()
            for line in rec.order_line:
                line.set_disc_value()
                line.discount_method = 'fix'

    @api.onchange('discount_method')
    def set_disc_value(self):
        for rec in self:
            # rec.write({
            #     'discount_amount': 0,
            #     'multi_discount': "0",
            # })
            rec.discount_amount = 0
            rec.multi_discount = '0'

    @api.onchange('discount_amount', 'multi_discount')
    def _set_discount_line(self):
        for res in self:
            if res.discount_amount or res.discount_amount == 0:
                tax_discount_policy = res.tax_discount_policy
                gross_total = 0
                for line in res.order_line:
                    if not line.is_down_payment:
                        gross_total += line.product_uom_qty*line.price_unit

                for line in res.order_line:
                    if not line.is_down_payment:
                        if not line.is_promotion_disc_product_line:
                            if tax_discount_policy == 'tax':
                                if res.discount_type == 'global':
                                    if res.discount_method == 'fix':
                                        line.discount_amount = (res.discount_amount/gross_total)*(line.product_uom_qty*line.price_unit) if gross_total > 0 else 0
                                    else:
                                        line.discount_amount = res.discount_amount
                                else:
                                    line.discount_amount = res.discount_amount
                            else:
                                if res.discount_type == 'global':
                                    if res.discount_method == 'fix':
                                        line.discount_amount = (res.discount_amount/gross_total)*(line.product_uom_qty*line.price_unit) if gross_total > 0 else 0
                                    else:
                                        line.discount_amount = res.discount_amount
                                else:
                                    line.discount_amount = res.discount_amount

                        line.discount_method = res.discount_method
                        # if res.multilevel_disc:
                        #     line.multi_discount = res.multi_discount
                        line.multi_discount = res.multi_discount

    @api.onchange('partner_id')
    def set_del_add_line(self):
        for res in self:
            if self.partner_id and self.partner_id.is_limit_salesperson:
                message = "Quotation for this customer can only be made by salesperson for that customer"
                if not self.partner_id.user_id:
                    self.partner_id = False
                    self.partner_invoice_id = False
                    self.partner_shipping_id = False
                    return {'warning': {
                        'title': _('Warning'),
                        'message': _(message)
                    }}
                elif self.partner_id.user_id and self.partner_id.user_id.id != self.env.uid:
                    self.partner_id = False
                    self.partner_invoice_id = False
                    self.partner_shipping_id = False
                    return {'warning': {
                        'title': _('Warning'),
                        'message': _(message)
                    }}
            if res.order_line:
                address = self.env['res.partner'].search([('type', '=', 'delivery'), ('parent_id', '=', res.partner_id.id)], limit=1)
                if not isinstance(res.id, models.NewId):
                    if address:
                        self._cr.execute("""UPDATE sale_order_line SET delivery_address_id = %s WHERE id in %s""", (address.id, tuple(res.order_line.ids)))
                        self._cr.commit()
                    else:
                        self._cr.execute("""UPDATE sale_order_line SET delivery_address_id = %s WHERE id in %s""", (res.partner_id.id, tuple(res.order_line.ids)))
                        self._cr.commit()
                else:
                    for line in res.order_line:
                        if address:
                            line.delivery_address_id = address.id
                        else:
                            line.delivery_address_id = res.partner_id.id
                    # line._compute_partner_address()


    @api.depends('picking_ids.state','state')
    def _compute_delivery(self):
        for res in self:
            qty_delivered = 0
            count_delivered = 0
            if res.state == 'sale':
                self.env.cr.execute("""
                    SELECT sum(qty_delivered), sum(product_uom_qty)
                    FROM sale_order_line
                    WHERE order_id = %s
                """ % res.id)
                count = self.env.cr.fetchall()
                qty_delivered = count[0][0]
                count_delivered = count[0][1]
            res.qty_delivered = qty_delivered
            res.count_delivered = count_delivered
            if res.qty_delivered < 1:
                res.delivered_state = 'pending'
            elif 1 <= res.qty_delivered < res.count_delivered:
                res.delivered_state = 'partially'
            else:
                res.delivered_state = 'fully'

    @api.depends('state')
    def _compute_is_print_report(self):
        for record in self:
            record.is_print_report = False
            if record.state == "sale":
                record.is_print_report = True
            elif record.state == "draft":
                record.is_print_report = True
            elif record.state == "quotation_approved":
                record.is_print_report = True

    def action_show_revisions(self):
        context = dict(self.env.context) or {}
        revision_id = self.search([('parent_saleorder_id', '=', self.id)], limit=1)
        context.update({'active_id': revision_id.id})
        return {
            'name': 'Revision Sale Orders',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'domain': [('parent_saleorder_id', '=', self.id)],
            'context': context,
            'target': 'current',
        }

    def quotation_send_report(self):
        return self.env.ref('sale.action_report_saleorder').report_action(self)

    def proforma_invoice_send_report(self):
        return self.env.ref('sale.action_report_pro_forma_invoice').report_action(self)

    def _prepare_confirmation_values(self):
        return {
            'state': 'sale',
        }

    def so_revision_quote(self):
        for cur_rec in self:
            if cur_rec.is_revision_so:
                so_count = self.search([("revised_sale_order_id", '=', cur_rec.revised_sale_order_id.id)])
                split_name = self.name.split('/')
                if split_name[-1].startswith('R'):
                    split_name[-1] = 'R%d' % (len(so_count) + 1)
                else:
                    split_name.append('R%d' % (len(so_count) + 1))
                name = '/'.join(split_name)
            else:
                so_count = self.search([("revised_sale_order_id", '=', cur_rec.id)])
                name = _('%s/R%d') % (self.name, len(so_count) + 1)
            if cur_rec.is_revision_so:
                cur_id = self.revised_sale_order_id.id
            else:
                cur_id = self.id
            vals = {
                'name': name,
                'state': 'draft',
                'parent_saleorder_id': self.id,
                'revised_sale_order_id': cur_id,
                'is_revision_so': True
            }
            new_sale_id = cur_rec.copy(default=vals)
            cur_rec.write({'state': 'revised'})
            new_sale_id.write({
                'name': name,
                'origin': self.name,
            })
            new_sale_id._compute_approving_customer_matrix()
            new_sale_id._compute_approving_matrix_lines()
            if cur_rec.is_revision_so:
                new_sale_id.revised_sale_order_ids = [(6, 0, new_sale_id.revised_sale_order_id.ids + so_count.ids)]
            else:
                new_sale_id.revised_sale_order_ids = [(6, 0, self.ids)]

    # @api.constrains('pricelist_id', 'order_line')
    # def _check_product_price(self):
    #     for order in self:
    #         if order.order_line:
    #             for record in order.order_line:
    #                 sale_product_id = record.product_id.id
    #                 sale_price_unit = record.price_unit
    #                 sale_product_uom = record.product_uom.id
    #                 sale_min_qty = record.product_uom_qty #changed
    #                 sale_order_date = order.date_order
    #                 margin = record.margin / record.product_uom_qty
    #                 if len(order.pricelist_id.item_ids) > 0:
    #                     for list_items in order.pricelist_id.item_ids:
    #                         item_uom = list_items.pricelist_uom_id.id
    #                         min_price = list_items.minimum_price
    #                         max_price = list_items.maximum_price
    #                         item_min_qty = list_items.min_quantity
    #                         item_date_start = list_items.date_start
    #                         item_date_end = list_items.date_end
    #                         check_min_max = False
    #                         if list_items.applied_on == '3_global':
    #                                 if item_uom and item_min_qty and item_date_start and item_date_end:
    #                                     if sale_product_uom == item_uom and sale_min_qty >= item_min_qty \
    #                                             and sale_order_date >= item_date_start and sale_order_date <= item_date_end:
    #                                         check_min_max = True
    #                                 elif item_uom and item_min_qty and item_date_start:
    #                                     if sale_product_uom == item_uom and sale_min_qty >= item_min_qty \
    #                                             and sale_order_date >= item_date_start:
    #                                         check_min_max = True
    #                                 elif item_uom and item_min_qty and item_date_end:
    #                                     if sale_product_uom == item_uom and sale_min_qty >= item_min_qty \
    #                                             and sale_order_date <= item_date_end:
    #                                         check_min_max = True
    #                                 elif item_uom and item_min_qty:
    #                                     if sale_product_uom == item_uom and sale_min_qty >= item_min_qty:
    #                                         check_min_max = True

    #                                 elif item_min_qty and item_date_start and item_date_end:
    #                                     if sale_min_qty >= item_min_qty and sale_order_date >= item_date_start and sale_order_date <= item_date_end:
    #                                         check_min_max = True
    #                                 elif item_min_qty and item_date_start:
    #                                     if sale_min_qty >= item_min_qty and sale_order_date >= item_date_start:
    #                                         check_min_max = True
    #                                 elif item_min_qty and item_date_end:
    #                                     if sale_min_qty >= item_min_qty and sale_order_date <= item_date_end:
    #                                         check_min_max = True

    #                                 elif sale_min_qty >= item_min_qty:
    #                                         check_min_max = True

    #                         elif list_items.applied_on == '0_product_variant':
    #                             price_product_id = list_items.product_id.id
    #                             if sale_product_id == price_product_id:
    #                                 if item_uom and item_min_qty and item_date_start and item_date_end:
    #                                     if sale_product_uom == item_uom and sale_min_qty >= item_min_qty \
    #                                             and sale_order_date >= item_date_start and sale_order_date <= item_date_end:
    #                                         check_min_max = True
    #                                 elif item_uom and item_min_qty and item_date_start:
    #                                     if sale_product_uom == item_uom and sale_min_qty >= item_min_qty \
    #                                             and sale_order_date >= item_date_start:
    #                                         check_min_max = True
    #                                 elif item_uom and item_min_qty and item_date_end:
    #                                     if sale_product_uom == item_uom and sale_min_qty >= item_min_qty \
    #                                             and sale_order_date <= item_date_end:
    #                                         check_min_max = True
    #                                 elif item_uom and item_min_qty:
    #                                     if sale_product_uom == item_uom and sale_min_qty >= item_min_qty:
    #                                         check_min_max = True

    #                                 elif item_min_qty and item_date_start and item_date_end:
    #                                     if sale_min_qty >= item_min_qty and sale_order_date >= item_date_start and sale_order_date <= item_date_end:
    #                                         check_min_max = True
    #                                 elif item_min_qty and item_date_start:
    #                                     if sale_min_qty >= item_min_qty and sale_order_date >= item_date_start:
    #                                         check_min_max = True
    #                                 elif item_min_qty and item_date_end:
    #                                     if sale_min_qty >= item_min_qty and sale_order_date <= item_date_end:
    #                                         check_min_max = True

    #                                 elif sale_min_qty >= item_min_qty:
    #                                         check_min_max = True

    #                         elif list_items.applied_on == '1_product':
    #                             sale_product_id = record.product_template_id.id
    #                             price_product_id = list_items.product_tmpl_id.id
    #                             if sale_product_id == price_product_id:
    #                                 if item_uom and item_min_qty and item_date_start and item_date_end:
    #                                     if sale_product_uom == item_uom and sale_min_qty >= item_min_qty \
    #                                             and sale_order_date >= item_date_start and sale_order_date <= item_date_end:
    #                                         check_min_max = True
    #                                 elif item_uom and item_min_qty and item_date_start:
    #                                     if sale_product_uom == item_uom and sale_min_qty >= item_min_qty \
    #                                             and sale_order_date >= item_date_start:
    #                                         check_min_max = True
    #                                 elif item_uom and item_min_qty and item_date_end:
    #                                     if sale_product_uom == item_uom and sale_min_qty >= item_min_qty \
    #                                             and sale_order_date <= item_date_end:
    #                                         check_min_max = True
    #                                 elif item_uom and item_min_qty:
    #                                     if sale_product_uom == item_uom and sale_min_qty >= item_min_qty:
    #                                         check_min_max = True

    #                                 elif item_min_qty and item_date_start and item_date_end:
    #                                     if sale_min_qty >= item_min_qty and sale_order_date >= item_date_start and sale_order_date <= item_date_end:
    #                                         check_min_max = True
    #                                 elif item_min_qty and item_date_start:
    #                                     if sale_min_qty >= item_min_qty and sale_order_date >= item_date_start:
    #                                         check_min_max = True
    #                                 elif item_min_qty and item_date_end:
    #                                     if sale_min_qty >= item_min_qty and sale_order_date <= item_date_end:
    #                                         check_min_max = True

    #                                 elif sale_min_qty >= item_min_qty:
    #                                         check_min_max = True

    #                         elif list_items.applied_on == '2_product_category':
    #                             sale_categ_id = record.product_id.categ_id.id
    #                             price_categ_id = list_items.categ_id.id
    #                             if sale_categ_id == price_categ_id:
    #                                 if item_uom and item_min_qty and item_date_start and item_date_end:
    #                                     if sale_product_uom == item_uom and sale_min_qty >= item_min_qty \
    #                                             and sale_order_date >= item_date_start and sale_order_date <= item_date_end:
    #                                         check_min_max = True
    #                                 elif item_uom and item_min_qty and item_date_start:
    #                                     if sale_product_uom == item_uom and sale_min_qty >= item_min_qty \
    #                                             and sale_order_date >= item_date_start:
    #                                         check_min_max = True
    #                                 elif item_uom and item_min_qty and item_date_end:
    #                                     if sale_product_uom == item_uom and sale_min_qty >= item_min_qty \
    #                                             and sale_order_date <= item_date_end:
    #                                         check_min_max = True
    #                                 elif item_uom and item_min_qty:
    #                                     if sale_product_uom == item_uom and sale_min_qty >= item_min_qty:
    #                                         check_min_max = True

    #                                 elif item_min_qty and item_date_start and item_date_end:
    #                                     if sale_min_qty >= item_min_qty and sale_order_date >= item_date_start and sale_order_date <= item_date_end:
    #                                         check_min_max = True
    #                                 elif item_min_qty and item_date_start:
    #                                     if sale_min_qty >= item_min_qty and sale_order_date >= item_date_start:
    #                                         check_min_max = True
    #                                 elif item_min_qty and item_date_end:
    #                                     if sale_min_qty >= item_min_qty and sale_order_date <= item_date_end:
    #                                         check_min_max = True

    #                                 elif sale_min_qty >= item_min_qty:
    #                                         check_min_max = True

    #                         product_name = f"[{record.product_id.default_code}] {record.product_id.name}"
    #                         if check_min_max and min_price > 0 and max_price > 0:
    #                             if (sale_price_unit < min_price):
    #                                 raise Warning(f"{product_name} unit price is below the minimum price")
    #                             if (sale_price_unit > max_price):
    #                                 raise Warning(f"{product_name} unit price is above the maximum price")
    #                             # break
    #                         elif check_min_max and min_price > 0:
    #                             if (sale_price_unit < min_price):
    #                                 raise Warning(f"{product_name} unit price is below the minimum price")
    #                             # break
    #                         elif check_min_max and max_price > 0:
    #                             if (sale_price_unit > max_price):
    #                                 raise Warning(f"{product_name} unit price is above the maximum price")
    #                             # break
    #                         if list_items.compute_price == 'formula' and check_min_max:
    #                             min_margin = list_items.price_min_margin
    #                             max_margin = list_items.price_max_margin
    #                             if min_margin > 0:
    #                                 if margin < min_margin:
    #                                     raise Warning(f"{product_name} margin is below the minimum margin on the selected pricelist")
    #                             if max_margin > 0:
    #                                 if margin > max_margin:
    #                                     raise Warning(f"{product_name} margin is above the maximum margin on the selected pricelist")



    @api.constrains('order_line')
    def _check_product_location(self):
        pass

    @api.onchange('commitment_date','warehouse_new_id')
    def check_sale_line(self):
        for order in self:
            temp_list = []
            line_list_vals = []
            if self.user_has_groups('equip3_sale_operation.group_multi_do'):
                for record in order.order_line.filtered(lambda r: not r.display_type):
                    if not record.id.origin and not record.id.ref:
                        continue
                    record.multiple_do_date = record.multiple_do_date_new
                    # record.line_warehouse_id = record.line_warehouse_id_new
                    if record.multiple_do_date:
                        multiple_do_date = record.multiple_do_date.date()
                    else:
                        multiple_do_date = False
                    if {'line_warehouse_id': record.line_warehouse_id.id,
                        'delivery_address_id': record.delivery_address_id.id,
                        'delivery_date': multiple_do_date,
                        'product_id': record.product_id.id} in temp_list:
                        raise ValidationError('You cannot add same Product, Warehouse, Delivery Address and Delivery Date Record Twice!')
                    else:
                        temp_list.append({
                            'line_warehouse_id': record.line_warehouse_id.id,
                            'delivery_address_id': record.delivery_address_id.id,
                            'delivery_date': multiple_do_date,
                            'product_id': record.product_id.id
                        })
            else:
                for record in order.order_line.filtered(lambda r: not r.display_type):
                    if not record.id.origin and not record.id.ref:
                        continue
                    if {'line_warehouse_id': record.line_warehouse_id.id,
                        'product_id': record.product_id.id} in temp_list:
                        raise ValidationError('You cannot add same product with the same warehouse twice.')
                    else:
                        temp_list.append({
                            'line_warehouse_id': record.line_warehouse_id.id,
                            'product_id': record.product_id.id,
                        })


    def _compute_group_multi_do(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        for record in self:
            record.group_multi_do = IrConfigParam.get_param('group_multi_do', False)

    @api.onchange('commitment_date', 'is_single_delivery_date')
    def onchange_delivery_date(self):
        for record in self:
            if record.is_single_delivery_date and record.commitment_date:
                record.order_line.write({
                    'multiple_do_date': record.commitment_date,
                    'multiple_do_date_new': record.commitment_date
                })

    @api.onchange('warehouse_id', 'is_single_warehouse')
    def onchange_destination_warehouse(self):
        for record in self:
            if record.is_single_warehouse and record.warehouse_id:
                for line in record.order_line:
                    # line.line_warehouse_id = record.warehouse_id
                    line.line_warehouse_id_new = record.warehouse_id

    @api.onchange('terms_conditions_id')
    def _onchange_terms_conditions_id(self):
        # self._compute_group_multi_do()
        if self.terms_conditions_id:
            self.note = self.terms_conditions_id.terms_and_conditions

    @api.onchange('account_tag_ids')
    def set_account_group_lines(self):
        # self._compute_group_multi_do()
        for res in self:
            for line in res.order_line:
                line.account_tag_ids = res.account_tag_ids

    @api.depends('company_id')
    def get_analytic_accounting(self):
        for res in self:
            res.analytic_accounting = res.user_has_groups('analytic.group_analytic_tags')

    @api.onchange('branch_id')
    def set_analytic_tag_ids(self):
        for res in self:
            analytic_priority_ids = self.env['analytic.priority'].search([], order="priority")
            for analytic_priority in analytic_priority_ids:
                if analytic_priority.object_id == 'user' and self.env.user.analytic_tag_ids:
                    res.update({
                        'account_tag_ids': [(6, 0, self.env.user.analytic_tag_ids.filtered(lambda a:a.company_id and a.company_id.id == self.env.company.id).ids)]
                    })
                    break
                elif analytic_priority.object_id == 'branch' and self.env.branch.analytic_tag_ids:
                    res.update({
                        'account_tag_ids': [(6, 0, self.env.branch.analytic_tag_ids.filtered(lambda a:a.company_id and a.company_id.id == self.env.company.id).ids)]
                    })
                    break

    @api.model
    def default_get(self, fields):
        res = super(SaleOrder, self).default_get(fields)
        analytic_priority_ids = self.env['analytic.priority'].search([], order="priority")
        for analytic_priority in analytic_priority_ids:
            if analytic_priority.object_id == 'user' and self.env.user.analytic_tag_ids:
                res.update({
                    'account_tag_ids': [(6, 0, self.env.user.analytic_tag_ids.filtered(lambda a:a.company_id and a.company_id.id == self.env.company.id).ids)]
                })
                break
            elif analytic_priority.object_id == 'branch' and self.env.branch.analytic_tag_ids:
                res.update({
                    'account_tag_ids': [(6, 0, self.env.branch.analytic_tag_ids.filtered(lambda a:a.company_id and a.company_id.id == self.env.company.id).ids)]
                })
                break
        res['note'] = ""
        if 'default_branch_id' not in self.env.context:
            res['branch_id'] = self.env.company_branches[0].id if len(self.env.company_branches) == 1 else False
        else:
            res['branch_id'] = self.env.context['default_branch_id']
        res['sale_order_template_id'] = False
        product_pricelist_default = self.env.company.product_pricelist_default
        res['pricelist_id'] = product_pricelist_default.id if product_pricelist_default else False
        tax_discount_policy= self.env.company.tax_discount_policy or False
        res['tax_discount_policy'] = tax_discount_policy
        res['show_mobile'] = self.env['ir.config_parameter'].sudo().get_param('show_sale_barcode_mobile_type')
        res['continuously_scan_setting'] = self.env.company.sh_sale_bm_is_cont_scan
        res['multilevel_disc'] = self.env['ir.config_parameter'].sudo().get_param('multilevel_disc_sale')
        return res

    @api.depends('picking_ids')
    def _compute_picking_ids(self):
        res = super(SaleOrder, self)._compute_picking_ids()
        # if self.user_has_groups('equip3_sale_operation.group_multi_do'):
        for record in self:
            pickings = self.env['stock.picking'].search([('group_id', 'in', record.procurement_group_id.ids)])
            if pickings:
                record.delivery_count = len(pickings)
        return res

    def action_view_delivery(self):
        '''
        This function returns an action that display existing delivery orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        '''
        self = self.with_context(outgoing=False)
        procurement_group_id = self.env['procurement.group'].search([('sale_id', '=', self.id)])
        pickings = self.env['stock.picking'].search([('group_id', 'in', procurement_group_id.ids)])
        if len(pickings) > 1:
        # if self.user_has_groups('equip3_sale_operation.group_multi_do'):
            action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")
            if len(pickings) > 1:
                action['domain'] = [('id', 'in', pickings.ids)]
            elif pickings:
                form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
                if 'views' in action:
                    action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
                else:
                    action['views'] = form_view
                action['res_id'] = pickings.id
            # Prepare the context.
            picking_id = pickings.filtered(lambda l: l.picking_type_id.code == 'outgoing')
            if picking_id:
                picking_id = picking_id[0]
            else:
                picking_id = pickings[0]
            action['context'] = dict(self._context, default_partner_id=self.partner_id.id, default_picking_type_id=picking_id.picking_type_id.id, default_origin=self.name, default_group_id=picking_id.group_id.id)
            return action
        else:
            return super(SaleOrder,self).action_view_delivery()

    @api.depends('approving_matrix_sale_id','partner_id')
    def _compute_approval_matrix_filled(self):
        for record in self:
            record.is_approval_matrix_filled = False
            if record.approving_matrix_sale_id:
                record.is_approval_matrix_filled = True

    def _get_approve_button(self):
        for record in self:
            matrix_line = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
            if len(matrix_line) == 0:
                record.is_approve_button = False
                record.approval_matrix_line_id = False
            elif len(matrix_line) > 0:
                matrix_line_id = matrix_line[0]
                if self.env.user.id in matrix_line_id.user_name_ids.ids and self.env.user.id != matrix_line_id.last_approved.id:
                    record.is_approve_button = True
                    record.approval_matrix_line_id = matrix_line_id.id
                else:
                    record.is_approve_button = False
                    record.approval_matrix_line_id = False
            else:
                record.is_approve_button = False
                record.approval_matrix_line_id = False

    def action_quotation_sent(self):
        if self.filtered(lambda so: so.state not in ('draft', 'quotation_approved')):
            raise UserError(_('Only draft orders can be marked as sent directly.'))
        for order in self:
            order.message_subscribe(partner_ids=order.partner_id.ids)
        self.write({'state': 'sent'})

    @api.onchange('partner_id')
    def _set_domain_partner_invoice_id(self):
        b = {}
        if self.partner_id:
            if self.sale_order_template_id:
                self.order_line = False
                self.sale_order_template_id = False
            partner_inv_ids = self.partner_id.child_ids.filtered(lambda r:r.type == 'invoice').ids
            partner_shipping_ids = self.partner_id.child_ids.filtered(lambda r:r.type == 'delivery').ids
            b = {'domain': {'partner_invoice_id': [('id', 'in', partner_inv_ids)], 'partner_shipping_id': [('id', 'in', partner_shipping_ids)]}}
        return b

    # @api.onchange('partner_id')
    # def _onchange_sale_partner(self):
    # self._compute_is_customer_approval_matrix() sudah menggunakan depend partner_id
    # self._compute_approval_matrix_filled() ditambahkan di depend
    # self._compute_group_multi_do() tidak perlu di compute ulang ketika ganti partner

    @api.onchange('approving_matrix_sale_id')
    def _compute_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            counter = 0
            record.approved_matrix_ids = []
            hierarchy = ApprovalHierarchy()
            for line in record.approving_matrix_sale_id.approver_matrix_line_ids:
                if line.approver_types == "specific_approver":
                    counter += 1
                    data.append((0, 0, {
                        'sequence' : counter,
                        'user_name_ids' : [(6, 0, line.user_name_ids.ids)],
                        'minimum_approver' : line.minimum_approver,
                    }))
                elif line.approver_types == "by_hierarchy":
                    manager_ids = []
                    seq = 1
                    data_seq = 0
                    approvers = hierarchy.get_hierarchy(self, self.env.user.employee_id, data_seq, manager_ids, seq,
                                                        line.minimum_approver)
                    for user in approvers:
                        counter += 1
                        data.append((0, 0, {
                            'sequence': counter,
                            'user_name_ids': [(6, 0, [user])],
                            'minimum_approver': 1,
                        }))
            record.approved_matrix_ids = data

    def write(self, vals):
        # pengecekan agar pricelist dari quotation website shop tidak diganti oleh default pricelist company
        if 'pricelist_id' in vals:
            if self.website_id:
                if self.pricelist_id != vals['pricelist_id']:
                    vals['pricelist_id'] = self.pricelist_id.id
        # ---------------------------------------
        if 'sale_hidden_compute_field' in vals:
            sale_fully_delivered = False
            sale_partially_delivery = False
            sale_fully_paid = False
            sale_partially_paid = False
            if self.delivered_state and not vals['sale_hidden_compute_field']:
                if self.delivered_state == 'fully':
                    sale_fully_delivered = True
                    sale_partially_delivery = False
                elif self.delivered_state == 'partially':
                    sale_partially_delivery = True
                    sale_fully_delivered = False
            if self.invoice_ids and not vals['sale_hidden_compute_field']:
                sum_of_invoice_paid = 0
                partial = False
                for invoice_id in self.invoice_ids.filtered(lambda inv: inv.state not in ['cancel', 'draft']):
                    if invoice_id.payment_state == 'paid':
                        sum_of_invoice_paid += 1
                    elif invoice_id.payment_state == 'partial':
                        partial = True
                if sum_of_invoice_paid != 0:
                    if sum_of_invoice_paid < len(self.invoice_ids):
                        sale_partially_paid = True
                    else:
                        sale_fully_paid = True
                        sale_partially_paid = False
                else:
                    if partial:
                        sale_partially_paid

            changes = True if self.sale_fully_delivered != sale_fully_delivered or self.sale_partially_delivery != sale_partially_delivery or self.sale_partially_paid != sale_partially_paid or self.sale_fully_paid != sale_fully_paid else False
            if changes:
                vals['sale_fully_paid'] = sale_fully_paid
                vals['sale_partially_paid'] = sale_partially_paid
                vals['sale_fully_delivered'] = sale_fully_delivered
                vals['sale_partially_delivery'] = sale_partially_delivery
        res = super(SaleOrder, self).write(vals)
        if not self.recurring_invoice_ids:
            if self.state == 'sale' and self.recurring_invoices and self.invoicing_policy == 'deliver':
                self.env.cr.execute("""
                        SELECT sum(qty_delivered), sum(product_uom_qty)
                        FROM sale_order_line
                        WHERE order_id = %s and is_recurring = True
                    """ % self.id)
                count_recurring = self.env.cr.fetchall()
                qty_delivered_recurring = count_recurring[0][0]
                count_delivered_recurring = count_recurring[0][1]
                if qty_delivered_recurring == count_delivered_recurring:
                    self.create_simulation_recurring()
                    self.create_invoice_recurring(self)
        if self.recurring_interval and not self.recurring_rule_type:
            raise ValidationError('you have to fill in recurring type')
        return res

    @api.model
    def create(self, vals):
        if 'recurring_interval' in vals:
            if vals['recurring_interval'] > 0:
                if 'recurring_rule_type' in vals:
                    if not vals['recurring_rule_type']:
                        raise ValidationError('you have to fill in recurring type')

        if 'order_line' in vals:
            if not vals['order_line']:
                raise ValidationError("Can't save quotation because there's no product in order line!")

        res = super(SaleOrder, self).create(vals)
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        auto_mail = IrConfigParam.get_param('auto_mail', False)
        # self.env.ref('sale.model_sale_order_action_quotation_sent').unlink_action()
        if auto_mail:
            res.action_sale_send_mail()
        res._compute_approving_customer_matrix()
        res._compute_approving_matrix_lines()
        if not res.is_revision_so:
            res.state = 'draft'
            keep_name_so = IrConfigParam.get_param('keep_name_so', False)
            if keep_name_so:
                res.name = self.env['ir.sequence'].next_by_code('sale.order.quotation.order')
            else:
                res.name = self.env['ir.sequence'].next_by_code('sale.order.quotation')
        return res

    @api.onchange('order_line')
    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in sorted(rec.order_line, key=lambda x: x.sequence):
                if line.product_template_id and line.product_uom:
                    line.sale_line_sequence = current_sequence
                    current_sequence += 1

            # current_sequence = 1
            # for line in rec.order_line:
            #     if line.product_template_id and line.product_uom:
            #         line.sale_line_sequence = current_sequence
            #         current_sequence += 1

    def order_confirm(self):
        res = super(SaleOrder, self).order_confirm()
        for record in self:
            IrConfigParam = self.env['ir.config_parameter'].sudo()
            auto_mail = IrConfigParam.get_param('auto_mail', False)
            if auto_mail:
                record.action_sale_send_mail()
        return res

    def action_sale_send_mail(self):
        template_id = self._find_mail_template()
        lang = self.env.context.get('lang')
        template = self.env['mail.template'].browse(template_id)
        if template.lang:
            lang = template._render_lang(self.ids)[self.id]

        if self.state != 'sale':
            subject = '%s Quotation (Ref %s)'%(self.company_id.name, self.name)
        else:
            subject = '%s Order (Ref %s)'%(self.company_id.name, self.name)

        body = self.env['mail.render.mixin']._render_template(template.body_html, 'sale.order', self.ids)[self.id]
        ctx = {
            'default_body': body,
            'default_subject': subject,
            'default_model': 'sale.order',
            'default_partner_ids': self.partner_id.ids,
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'custom_layout': "mail.mail_notification_paynow",
            'proforma': self.env.context.get('proforma', False),
            'force_email': True,
            'model_description': self.with_context(lang=lang).type_name,
        }
        mail_compose_message_id = self.env['mail.compose.message'].with_context(ctx).create({})
        values = mail_compose_message_id.generate_email_for_composer(
            template.id, [self.id],
            ['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc',  'reply_to', 'attachment_ids', 'mail_server_id']
        )[self.id]
        attachment_ids = []
        Attachment = self.env['ir.attachment']
        for attach_fname, attach_datas in values.pop('attachments', []):
            data_attach = {
                'name': attach_fname,
                'datas': attach_datas,
                'res_model': 'mail.compose.message',
                'res_id': 0,
                'type': 'binary',  # override default_type from context, possibly meant for another model!
            }
            attachment_ids.append(Attachment.create(data_attach).id)
        mail_compose_message_id.attachment_ids = [(6, 0, attachment_ids)]
        # mail_compose_message_id.send_mail()
        mail_message_id = self.env['mail.message'].search([('res_id', '=', self.id), ('model', '=', 'sale.order')], limit=1)
        mail_message_id.write({'subject': subject})
        mail_message_id.res_id = 0
        if self.state != 'sale':
            self.message_post(body=_("Email has been sent to %s for Quotation information") % self.partner_id.name)
        else:
            self.message_post(body=_("Email has been sent to %s for Sale Order confirmation") % self.partner_id.name)

    @api.depends('partner_id')
    def _compute_is_customer_approval_matrix(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_customer_approval_matrix = IrConfigParam.get_param('is_customer_approval_matrix')
        is_customer_limit_matrix = IrConfigParam.get_param('is_customer_limit_matrix')
        for record in self:
            record.is_customer_approval_matrix = is_customer_approval_matrix
            if is_customer_limit_matrix or is_customer_approval_matrix and record.state != "quotation_approved":
                record.hide_proforma = True
            else:
                record.hide_proforma = False

    @api.depends('amount_total', 'margin_percent', 'discount_amt', 'discount_amt_line', 'branch_id', 'currency_id')
    def _compute_approving_customer_matrix(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_total_amount = IrConfigParam.get_param('is_total_amount', False)
        is_margin_amount = IrConfigParam.get_param('is_margin_amount', False)
        is_discount_amount = IrConfigParam.get_param('is_discount_amount', False)
        total_sequence = IrConfigParam.get_param('total_sequence', 0)
        margin_sequence = IrConfigParam.get_param('margin_sequence', 0)
        discount_sequence = IrConfigParam.get_param('discount_sequence', 0)
        data = []
        if is_total_amount:
            data.insert(int(total_sequence) - 1, 'total_amt')
        if is_margin_amount:
            data.insert(int(margin_sequence) - 1, 'pargin_per')
        if is_discount_amount:
            data.insert(int(discount_sequence) - 1, 'discount_amt')
        for record in self:
            matrix_ids = []
            if record.is_customer_approval_matrix:
                record.approving_matrix_sale_id = False
                for sale_matrix_config in data:
                    if sale_matrix_config == 'total_amt':
                        matrix_id = self.env['approval.matrix.sale.order'].search([('config', '=', 'total_amt'),
                                    ('minimum_amt', '<=', record.amount_total),
                                    ('maximum_amt', '>=', record.amount_total),
                                    ('company_id', '=', record.company_id.id), ('branch_id', '=', record.branch_id.id),('currency_id', '=', record.currency_id.id)], limit=1)
                        if matrix_id:
                            matrix_ids.append(matrix_id.id)
                    elif sale_matrix_config == 'pargin_per':
                        matrix_id = self.env['approval.matrix.sale.order'].search([('config', '=', 'pargin_per'),
                                    ('minimum_amt', '<=', record.margin_percent*100), ('maximum_amt', '>=', record.margin_percent*100),
                                    ('company_id', '=', record.company_id.id), ('branch_id', '=', record.branch_id.id),('currency_id', '=', record.currency_id.id)], limit=1)
                        if matrix_id:
                            matrix_ids.append(matrix_id.id)
                    elif sale_matrix_config == 'discount_amt':
                        if record.discount_type == 'line':
                            matrix_id = self.env['approval.matrix.sale.order'].search([('config', '=', 'discount_amt'),
                                        ('minimum_amt', '<=', record.discount_amt_line),
                                        ('maximum_amt', '>=', record.discount_amt_line),
                                        ('company_id', '=', record.company_id.id), ('branch_id', '=', record.branch_id.id),('currency_id', '=', record.currency_id.id)], limit=1)
                            if matrix_id:
                                matrix_ids.append(matrix_id.id)
                        else:
                            matrix_id = self.env['approval.matrix.sale.order'].search([('config', '=', 'discount_amt'),
                                        ('minimum_amt', '<=', record.discount_amt),
                                        ('maximum_amt', '>=', record.discount_amt),
                                        ('company_id', '=', record.company_id.id), ('branch_id', '=', record.branch_id.id),('currency_id', '=', record.currency_id.id)], limit=1)
                            if matrix_id:
                                matrix_ids.append(matrix_id.id)
                record.approving_matrix_sale_id = [(6, 0, matrix_ids)]
            else:
                record.approving_matrix_sale_id = False

    def action_confirm_approving(self):
        for record in self:
            record.write({'state': 'quotation_approved'})

    def action_request_for_approving(self):
        for record in self:
            record.action_request_for_approving_sale_matrix()

    def action_request_for_approving_sale_matrix(self):
        for record in self:
            is_email_so_approval = self.env['ir.config_parameter'].sudo().get_param('is_email_so_approval', False)
            is_wa_so_approval = self.env['ir.config_parameter'].sudo().get_param('is_wa_so_approval', False)
            action_id = self.env.ref('sale.action_quotations_with_onboarding')
            template_id = self.env.ref('equip3_sale_operation.email_template_internal_sale_order_approval')
            wa_template_id = self.env.ref('equip3_sale_operation.email_template_internal_sale_order_approval_wa')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=sale.order'
            if record.approved_matrix_ids and len(record.approved_matrix_ids[0].user_name_ids) > 1:
                for approved_matrix_id in record.approved_matrix_ids[0].user_name_ids:
                    approver = approved_matrix_id
                    ctx = {
                        'email_from' : self.env.user.company_id.email,
                        'email_to' : approver.partner_id.email,
                        'approver_name' : approver.name,
                        'date': date.today(),
                        'url' : url,
                    }
                    if is_email_so_approval:
                        template_id.with_context(ctx).send_mail(record.id, True)
                    if is_wa_so_approval:
                        phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                        # record._send_whatsapp_message_approval(wa_template_id, approver, phone_num, url)
                        record._send_qiscus_whatsapp_approval(wa_template_id, approver, phone_num, url)
            elif record.approved_matrix_ids:
                approver = record.approved_matrix_ids[0].user_name_ids[0]
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : approver.partner_id.email,
                    'approver_name' : approver.name,
                    'date': date.today(),
                    'url' : url,
                }
                if is_email_so_approval:
                    template_id.with_context(ctx).send_mail(record.id, True)
                if is_wa_so_approval:
                    phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                    # record._send_whatsapp_message_approval(wa_template_id, approver, phone_num, url)
                    record._send_qiscus_whatsapp_approval(wa_template_id, approver, phone_num, url)
            record.write({'state': 'waiting_for_approval'})

    def action_confirm_approving_matrix(self):
        for record in self:
            is_email_so_approval = self.env['ir.config_parameter'].sudo().get_param('is_email_so_approval', False)
            is_wa_so_approval = self.env['ir.config_parameter'].sudo().get_param('is_wa_so_approval', False)
            action_id = self.env.ref('sale.action_quotations_with_onboarding')
            template_id = self.env.ref('equip3_sale_operation.email_template_reminder_for_sale_order_approval')
            approved_template_id = self.env.ref('equip3_sale_operation.email_template_sale_order_approval_approved')

            wa_template_id = self.env.ref('equip3_sale_operation.email_template_reminder_for_sale_order_approval_wa')
            wa_approved_template_id = self.env.ref('equip3_sale_operation.email_template_sale_order_approval_approved_wa')

            user = self.env.user
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=sale.order'
            if record.is_approve_button and record.approval_matrix_line_id:
                approval_matrix_line_id = record.approval_matrix_line_id
                if user.id in approval_matrix_line_id.user_name_ids.ids and \
                    user.id not in approval_matrix_line_id.approved_users.ids:
                    name = approval_matrix_line_id.state_char or ''
                    if name != '':
                        name += "\n • %s: Approved" % (self.env.user.name)
                    else:
                        name += "• %s: Approved" % (self.env.user.name)

                    approval_matrix_line_id.write({
                        'last_approved': self.env.user.id, 'state_char': name,
                        'approved_users': [(4, user.id)]})
                    if approval_matrix_line_id.minimum_approver == len(approval_matrix_line_id.approved_users.ids):
                        approval_matrix_line_id.write({'time_stamp': datetime.now(), 'approved': True, 'approver_state': 'approved'})
                        approver_name = ' and '.join(approval_matrix_line_id.mapped('user_name_ids.name'))
                        next_approval_matrix_line_id = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
                        if next_approval_matrix_line_id and len(next_approval_matrix_line_id[0].user_name_ids) > 1:
                            for approving_matrix_line_user in next_approval_matrix_line_id[0].user_name_ids:
                                ctx = {
                                    'email_from' : self.env.user.company_id.email,
                                    'email_to' : approving_matrix_line_user.partner_id.email,
                                    'approver_name' : approving_matrix_line_user.name,
                                    'date': date.today(),
                                    'submitter' : approver_name,
                                    'url' : url,
                                }
                                if is_email_so_approval:
                                    template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                if is_wa_so_approval:
                                    phone_num = str(approving_matrix_line_user.partner_id.mobile) or str(approving_matrix_line_user.partner_id.phone)
                                    # record._send_whatsapp_message_approval(wa_template_id, approving_matrix_line_user, phone_num, url, submitter=approver_name)
                                    record._send_qiscus_whatsapp_approval(wa_template_id, approving_matrix_line_user,
                                                                           phone_num, url, submitter=approver_name)
                        else:
                            if next_approval_matrix_line_id and next_approval_matrix_line_id[0].user_name_ids:
                                ctx = {
                                    'email_from' : self.env.user.company_id.email,
                                    'email_to' : next_approval_matrix_line_id[0].user_name_ids[0].partner_id.email,
                                    'approver_name' : next_approval_matrix_line_id[0].user_name_ids[0].name,
                                    'date': date.today(),
                                    'submitter' : approver_name,
                                    'url' : url,
                                }
                                if is_email_so_approval:
                                    template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                if is_wa_so_approval:
                                    phone_num = str(next_approval_matrix_line_id[0].user_name_ids[0].partner_id.mobile) or str(next_approval_matrix_line_id[0].user_name_ids[0].partner_id.phone)
                                    # record._send_whatsapp_message_approval(wa_template_id, next_approval_matrix_line_id[0].user_name_ids[0], phone_num, url, submitter=approver_name)
                                    record._send_qiscus_whatsapp_approval(wa_template_id, next_approval_matrix_line_id[
                                        0].user_name_ids[0], phone_num, url, submitter=approver_name)
                    else:
                        approval_matrix_line_id.write({'approver_state': 'pending'})

            if len(record.approved_matrix_ids) == len(record.approved_matrix_ids.filtered(lambda r:r.approved)):
                record.write({'state': 'quotation_approved'})
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : record.user_id.partner_id.email,
                    'date': date.today(),
                    'url' : url,
                }
                if is_email_so_approval:
                    approved_template_id.sudo().with_context(ctx).send_mail(record.id, True)
                if is_wa_so_approval:
                    phone_num = str(record.create_uid.partner_id.mobile) or str(record.create_uid.partner_id.phone)
                    # record._send_whatsapp_message_approval(wa_approved_template_id, record.user_id.partner_id, phone_num, url)
                    record._send_qiscus_whatsapp_approval(wa_approved_template_id, record.user_id.partner_id,
                                                           phone_num, url)

    def _send_whatsapp_message_approval(self, template_id, approver, phone, url, submitter=False):
        for record in self:
            string_test = str(tools.html2plaintext(template_id.body_html))
            if "${date}" in string_test:
                string_test = string_test.replace("${date}", date.today().strftime(DEFAULT_SERVER_DATE_FORMAT))
            if "${approver_name}" in string_test:
                string_test = string_test.replace("${approver_name}", approver.name)
            if "${name}" in string_test:
                string_test = string_test.replace("${name}", record.name)
            if "${partner_name}" in string_test:
                string_test = string_test.replace("${partner_name}", record.user_id.partner_id.name)
            if "${submitter_name}" in string_test:
                string_test = string_test.replace("${submitter_name}", submitter)
            if "${br}" in string_test:
                string_test = string_test.replace("${br}", f"\n")
            if "${url}" in string_test:
                string_test = string_test.replace("${url}", url)
            phone_num = phone
            if "+" in phone_num:
                phone_num = phone_num.replace("+", "")
            param = {'body': string_test, 'phone': phone_num, 'previewBase64': '', 'title': ''}
            domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
            token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
            try:
                request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param, headers=headers, verify=True)
            except ConnectionError:
                raise ValidationError("Not connect to API Chat Server. Limit reached or not active")
                    # connector_id.ca_request('post', 'sendMessage', param)

    def format_amount_sale(self, amount, currency):
        if currency.position == 'before':
            return currency.symbol + " " + str(amount)
        else:
            return str(amount) + " " + currency.symbol

    def _send_qiscus_whatsapp_approval(self, template_id, approver, phone, url, submitter=False):
        self.ensure_one()
        for record in self:
            broadcast_template_id = self.env['qiscus.wa.template.content'].search([
                ('language', '=', 'en'),
                ('template_id.name', '=', 'hm_sale_notification_1')
            ], limit=1)
            if not broadcast_template_id:
                raise ValidationError(_("Cannot find Whatsapp template with name = 'hm_sale_notification_1'!"))
            domain = self.env['ir.config_parameter'].get_param('qiscus.api.url')
            token = self.env['ir.config_parameter'].get_param('qiscus.api.secret_key')
            app_id = self.env['ir.config_parameter'].get_param('qiscus.api.appid')
            channel_id = self.env['ir.config_parameter'].get_param('qiscus.api.channel_id')

            string_test = str(tools.html2plaintext(template_id.body_html))
            if "${date}" in string_test:
                string_test = string_test.replace("${date}", date.today().strftime(DEFAULT_SERVER_DATE_FORMAT))
            if "${approver_name}" in string_test:
                string_test = string_test.replace("${approver_name}", approver.name)
            if "${name}" in string_test:
                string_test = string_test.replace("${name}", record.name)
            if "${partner_name}" in string_test:
                string_test = string_test.replace("${partner_name}", record.user_id.partner_id.name)
            if "${submitter_name}" in string_test:
                string_test = string_test.replace("${submitter_name}", submitter)
            if "${br}" in string_test:
                string_test = string_test.replace("${br}", f"\n")
            if "${url}" in string_test:
                string_test = string_test.replace("${url}", url)
            if "${amount_total}" in string_test:
                amount = record.format_amount_sale(record.amount_total, record.currency_id)
                string_test = string_test.replace("${amount_total}", amount)
            if "${date_order}" in string_test:
                string_test = string_test.replace("${date_order}", str(record.date_order))
            # message = re.sub(r'\n+', ', ', string_test)
            messages = string_test.split(f'\n')
            message_obj = []
            for pesan in messages:
                message_obj.append({
                    'type': 'text',
                    'text': pesan
                })
            phone_num = phone
            if "+" in phone_num:
                phone_num = phone_num.replace("+", "").replace(" ", "").replace("-", "")
            headers = {
                'content-type': 'application/json',
                'Qiscus-App-Id': app_id,
                'Qiscus-Secret-Key': token
            }
            url = f'{domain}{app_id}/{channel_id}/messages'
            params = {
                "to": phone_num,
                "type": "template",
                "template": {
                    "namespace": broadcast_template_id.template_id.namespace,
                    "name": broadcast_template_id.template_id.name,
                    "language": {
                        "policy": "deterministic",
                        "code": 'en'
                    },
                    "components": [{
                        "type": "body",
                        "parameters": message_obj
                    }]
                }
            }
            try:
                request_server = requests.post(url, json=params, headers=headers, verify=True)
                _logger.info("\nNotification Whatsapp --> Request for Approval:\n-->Header: %s \n-->Parameter: %s \n-->Result: %s" % (headers, params, request_server.json()))
                # if request_server.status_code != 200:
                #     data = request_server.json()
                #     raise ValidationError(f"""{data["error"]["error_data"]["details"]}""")
            except ConnectionError:
                raise ValidationError("Not connect to API Chat Server. Limit reached or not active!")

    def action_reject_approving_matrix(self):
        for record in self:
            return {
                    'type': 'ir.actions.act_window',
                    'name': 'Reject Reason',
                    'res_model': 'approval.matrix.sale.reject',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                }

    def action_set_quotation(self):
        for record in self:
            record.approved_matrix_ids.write({
                            'approved_users': False,
                            'last_approved': False,
                            'approved': False,
                            'feedback': False,
                            'time_stamp': False,
                            'state_char': False,
                            })
            record.write({'state': 'draft'})

    @api.model
    def _action_sale_order_cancel(self):
        today_date = date.today()
        sale_order_ids = self.search([('validity_date', '<', today_date), ('state', 'in', ('draft', 'sent'))])
        sale_order_ids.write({'sale_state': 'cancel', 'state': 'cancel'})

    def action_cancel(self):
        for record in self:
            if record.state == 'sale':
                picking_ids = record.picking_ids
                invoice_ids = record.order_line.mapped('invoice_lines.move_id')
                if invoice_ids and any(invoice.state == 'posted' for invoice in invoice_ids) and \
                    picking_ids and any(picking.state == 'done' for picking in picking_ids):
                    raise ValidationError('You Cannot Cancel Confirmed SO!')
                elif invoice_ids and any(invoice.state == 'draft' for invoice in invoice_ids):
                    raise ValidationError('There is an unfinish invoice. Please cancel the invoice first!')
                else:
                    if picking_ids and any(picking.state == 'done' for picking in picking_ids):
                        raise ValidationError("You can't cancel Delivered SO!")
                    elif picking_ids and any(picking.state not in ('done', 'cancel') for picking in picking_ids):
                        raise ValidationError("There is an unfinish delivery order. Please cancel DO first!")
                    else:
                        record.write({'state': 'cancel', 'sale_state': 'cancel', 'is_quotation_cancel': False})
            else:
                record.write({'state': 'cancel', 'sale_state': 'cancel', 'is_quotation_cancel': True})

    def _action_confirm(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        for record in self:
            record.write({'date_confirm': datetime.today()})
            record.write({'sale_state': 'in_progress'})
            keep_name_so = IrConfigParam.get_param('keep_name_so', False)
            if not keep_name_so:
                if record.origin:
                    record.origin += "," + record.name
                else:
                    record.origin = record.name
                record.name = self.env['ir.sequence'].next_by_code('sale.quotation.order')
            # untuk asset tidak perlu dibedakan
            # record.order_line._action_launch_stock_rule_asset()
        res = super(SaleOrder, self)._action_confirm()
        if 'from_action_confirm' not in self.env.context:
            self.create_recurring_inv_sale()
        is_wa_so_approval = self.env['ir.config_parameter'].sudo().get_param('is_wa_so_approval', False)
        wa_template_id = self.env.ref('equip3_sale_operation.whatsapp_sales_template')
        if is_wa_so_approval:
            action_id = self.env.ref('sale.action_quotations_with_onboarding')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=sale.order'
            approver = record.create_uid
            phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
            self._send_qiscus_whatsapp_approval(wa_template_id, approver, phone_num, url)
        return res

    def unlink(self):
        for record in self:
            if record.picking_ids.filtered(lambda r: r.state == 'done') and record.invoice_ids.filtered(lambda l: l.state == 'posted' and l.payment_state == 'paid'):
                raise ValidationError("You Cannot Delete Confirmed SO!")
        return super(SaleOrder, self).unlink()

    def action_draft(self):
        orders = self.filtered(lambda s: s.state in ['cancel',
                            'sent', 'over_limit_reject', 'reject'])
        for order in orders:
            order.write({
                'state': 'draft',
                'sale_state': None,
                'is_quotation_cancel': False,
                'signature': False,
                'signed_by': False,
                'signed_on': False,
            })
            if order.approved_matrix_ids:
                order.approved_matrix_ids.write({
                    'approved': False,
                    'last_approved': False,
                    'state_char': '',
                    'time_stamp': False,
                    'approved_users': [(6, 0, [])],
                })

    def action_done(self):
        if 'from_action_confirm' not in self.env.context:
            return super().action_done()
        else:
            return True

    @api.depends('order_line')
    def order_line_calc(self):
        for record in self:
            record.order_line_count = len(record.order_line)

    @api.depends('state')
    def _compute_is_hidden_button(self):
        for rec in self:
            get_setting = self.env['ir.config_parameter'].sudo().get_param('show_select_product_button', False)
            rec.is_hidden_button = get_setting

    @api.depends('state')
    def _compute_lock_sale_order(self):
        for rec in self:
            get_setting = self.env['ir.config_parameter'].sudo().get_param('lock_sale_order')
            rec.lock_sale_order = get_setting

    @api.depends('discount_method','state','lock_sale_order')
    def _compute_readonly_disc(self):
        for rec in self:
            if rec.multilevel_disc:
                if rec.discount_method == 'per':
                    rec.readonly_disc = True
                    if rec.lock_sale_order:
                        if rec.state in ('sale','quotation_approved'):
                            rec.readonly_multi = True
                else:
                    rec.readonly_disc = False
                    if rec.lock_sale_order:
                        if rec.state in ('sale','quotation_approved'):
                            rec.readonly_disc = True
            else:
                if rec.lock_sale_order:
                    if rec.state in ('sale','quotation_approved'):
                        rec.readonly_disc = True
                else:
                    rec.readonly_disc = False

    def sh_sale_adv_btn(self):
        if self:
            for data in self:
                view = data.env.ref(
                    'equip3_sale_operation.sh_sale_adv_wizard_form_view'
                )
                ori_arch = """
    <form string="Select Products Advance">
                <notebook>
                    <page string="List">
                        <field name="product_ids">
                            <tree create="false" editable='bottom'>
                                <button name="add_to_specific" type="object" string="Add"/>
                                <field name="product_id" readonly="1" />
                                <field name="default_code" readonly="1" />
                                <field name="standard_price" readonly="1" />
                                <field name="uom_po_id" readonly="1" />
                                <field name="qty" />
                            </tree>
                        </field>
                    </page>
                    <page string="Specific">
                        <field name="specific_product_ids">
                            <tree create="false" editable='bottom'>
                                <field name="product_id" readonly="1" />
                                <field name="default_code" readonly="1" />
                                <field name="standard_price" readonly="1" />
                                <field name="uom_po_id" readonly="1" />
                                <field name="qty" />
                            </tree>
                        </field>
                    </page>
                </notebook>
                <footer>
                    <button name="sh_sale_adv_select_btn" string="Select List" type="object" class="oe_highlight"/>
                    <button name="sh_sale_adv_select_specific_btn" string="Select Specific" type="object" class="oe_highlight"/>
                    <button string="Cancel" class="oe_link" special="cancel"/>
                </footer>
            </form>

                """

                sh_cid = self.env.user.company_id
                sale_model_id = self.env[
                    'ir.model'
                ].sudo().search([
                    ('model', '=', 'sale.adv.wizard')
                ], limit=1)
                int_operators = [
                    ('=', '='),
                    ('!=', '!='),
                    ('>', '>'),
                    ('<', '<'),
                    ('>=', '>='),
                    ('<=', '<=')
                ]
                char_operators = [
                    ('=', '='),
                    ('!=', '!='),
                    ('like', 'like'),
                    ('ilike', 'ilike'),
                    ('=like', '=like'),
                    ('not like', 'not like'),
                    ('not ilike', 'not ilike')
                ]
                if sale_model_id and sh_cid:
                    ir_model_fields_obj = self.env['ir.model.fields']
                    str_obj = ori_arch
                    first_str = """<?xml version="1.0"?>
    <form string="Select Products Advance">
                    """

                    if sh_cid.sh_sale_pro_field_ids:
                        for rec in sh_cid.sh_sale_pro_field_ids:
                            #add custom selection operators fields here
                            if rec.ttype not in ['boolean', 'many2one', 'selection']:
                                search_opt_field = ir_model_fields_obj.sudo().search([
                                    ('name', '=', 'x_opt_'+ rec.name),
                                    ('model_id', '=', sale_model_id.id),
                                ], limit=1)
                                if not search_opt_field:
                                    opt_field_vals = {
                                        'name': 'x_opt_'+rec.name,
                                        'model': 'sale.adv.wizard',
                                        'field_description': 'x_opt_' + rec.field_description,
                                        'model_id': sale_model_id.id,
                                        'ttype': 'selection',
                                    }
                                    if rec.ttype in ['integer', 'float']:
                                        opt_field_vals.update({
                                            'selection': str(int_operators)
                                        })
                                    if rec.ttype == 'char':
                                        opt_field_vals.update({
                                            'selection': str(char_operators)
                                        })
                                    ir_model_fields_obj.sudo().create(opt_field_vals)

                            #create duplicate fields from product.product
                            #first search field if not found than create it.
                            search_field = ir_model_fields_obj.sudo().search([
                                ('name', '=', 'x_'+ rec.name),
                                ('model_id', '=', sale_model_id.id),
                            ], limit = 1)
                            #update selection fields key value pair each time when wizard is load
                            if search_field and search_field.ttype == 'selection':
                                selection_key_value_list = False
                                selection_key_value_list = self.env[
                                    rec.model
                                ].sudo()._fields[
                                    rec.name
                                ].selection
                                if selection_key_value_list:
                                    selection_field_dic = {}
                                    selection_field_dic.update({
                                        'selection': str(selection_key_value_list)
                                    })
                                    search_field.sudo().write(selection_field_dic)
                                else:
                                    raise UserError(
                                        _('Key value pair for this selection field not found - '+ search_field.name
                                          ))

                            selection_key_value_list = False
                            #crate new custome field here
                            if not search_field:
                                field_vals = {
                                    'name': 'x_'+rec.name,
                                    'model': 'sale.adv.wizard',
                                    'field_description': rec.field_description,
                                    'model_id': sale_model_id.id,
                                    'ttype': rec.ttype,
                                }
                                if rec.relation:
                                    field_vals.update({'relation': rec.relation})
                                if rec.ttype == 'selection':
                                    selection_key_value_list = self.env[
                                        rec.model
                                    ].sudo()._fields[
                                        rec.name
                                    ].selection
                                    if selection_key_value_list:
                                        field_vals.update({
                                            'selection': str(selection_key_value_list)
                                        })
                                    else:
                                        raise UserError(
                                            _('Key value pair for this selection field not found - '+ rec.name
                                              ))
                                ir_model_fields_obj.sudo().create(field_vals)

                    #product attributes code start here
                    #create attributes m2o fields if never exist
                    if sh_cid.sh_sale_pro_attr_ids:
                        for rec in sh_cid.sh_sale_pro_attr_ids:
                            search_attr_field = ir_model_fields_obj.sudo().search([
                                ('name', '=', 'x_attr_' + str(rec.id)),
                                ('model_id', '=', sale_model_id.id),
                            ], limit = 1)
                            if not search_attr_field:
                                attr_field_vals = {
                                    'name': 'x_attr_' + str(rec.id),
                                    'model': 'sale.adv.wizard',
                                    'field_description': rec.name,
                                    'model_id': sale_model_id.id,
                                    'ttype': 'many2one',
                                    'relation': 'product.attribute.value'
                                }
                                ir_model_fields_obj.sudo().create(attr_field_vals)

                    no_create_str = """ options="{'no_create': True }" """
                    middle_str = ''
                    if sh_cid.sh_sale_pro_field_ids:
                        for rec in sh_cid.sh_sale_pro_field_ids:
                            middle_str += "<div class='row' style='border-bottom:1px solid #ccc; margin:5px 10px;margin: 9px 0px;'>"
                            middle_str += "<div class='col-sm-3 text-right' style='font-weight:bold'> <label for='x_" + rec.name + "'/></div>"
                            if rec.ttype not in ['boolean','many2one','selection']:
                                middle_str += "<div class='col-sm-3'> <field name='x_opt_" + rec.name + "'/></div>"
                            if rec.ttype == 'many2one':
                                middle_str += "<div class='col-sm-3'> <field name='x_" + rec.name + "' "+ ' ' + no_create_str+"/></div>"
                            elif rec.ttype in ['boolean','selection']:
                                middle_str += "<div class='col-sm-3'> <field name='x_" + rec.name + "'/></div>"
                            else:
                                middle_str += "<div class='col-sm-6'> <field name='x_" + rec.name + "'/></div>"
                            middle_str += "</div>"

                    #add prodduct attributes fields in wizard view
                    if sh_cid.sh_sale_pro_attr_ids:
                        for rec in sh_cid.sh_sale_pro_attr_ids:
                            domain_str = """ domain="[('attribute_id','=',""" +  str(rec.id) + """)]" """
                            middle_str += "<div class='row' style='border-bottom:1px solid #ccc; margin:5px 10px;margin: 9px 0px;'>"
                            middle_str += "<div class='col-sm-3 text-right' style='font-weight:bold'> <label for='x_attr_" + str(rec.id) + "'/></div>"
                            middle_str += "<div class='col-sm-3'> <field name='x_attr_" + str(rec.id) + "' "+  domain_str +' '+ no_create_str +"/></div>"
                            middle_str += "<div class='col-sm-6'> </div>"
                            middle_str += "</div>"


                    #add the many2many attribute fields here.
                    no_create_str = """ options="{'no_create': True}" """
                    middle_str += "<div class='row' style='border-bottom:1px solid #ccc; margin:5px 10px;margin: 9px 0px;'>"
                    middle_str += "<div class='col-sm-3 text-right' style='font-weight:bold'> <label for='product_attr_ids'/> </div>"
                    middle_str += "<div class='col-sm-6'> <field name='product_attr_ids' widget='many2many_tags'"+' '+ no_create_str +"/> </div>"
                    middle_str += "</div>"

                    #button start here
                    middle_str += "<div class='col-md-12 text-center'>"
                    middle_str += "<button name='filter_products' string='Filter Products' type='object'/>"
                    middle_str += "<button name='reset_filter' string='Reset Filter' type='object'/>"
                    middle_str += "<button name='reset_list' string='Reset List' type='object'/>"
                    middle_str += "<button name='reset_specific' string='Reset Specific' type='object'/>"
                    middle_str += "</div>"
                    last_str = str_obj.split(">",1)[1]
                    final_arch = first_str + middle_str + last_str

                    if view:
                        view.sudo().write({'arch': final_arch})

                context = self.env.context
                return {
                    'name': 'Select Products Advance',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'sale.adv.wizard',
                    'views': [(view.id, 'form')],
                    'view_id': view.id,
                    'target': 'new',
                    'context': context,
                }

    def _create_delivery_line(self, carrier, price_unit):
        SaleOrderLine = self.env['sale.order.line']
        SaleOrderLine_rec = SaleOrderLine.search([('order_id', '=', self.id)], limit=1)

        if self.partner_id:
            # set delivery detail in the customer language
            carrier = carrier.with_context(lang=self.partner_id.lang)

        # Apply fiscal position
        taxes = carrier.product_id.taxes_id.filtered(lambda t: t.company_id.id == self.company_id.id)
        taxes_ids = taxes.ids
        if self.partner_id and self.fiscal_position_id:
            taxes_ids = self.fiscal_position_id.map_tax(taxes, carrier.product_id, self.partner_id).ids

        # Create the sales order line
        carrier_with_partner_lang = carrier.with_context(lang=self.partner_id.lang)
        if carrier_with_partner_lang.product_id.description_sale:
            so_description = '%s: %s' % (carrier_with_partner_lang.name,
                                        carrier_with_partner_lang.product_id.description_sale)
        else:
            so_description = carrier_with_partner_lang.name
        values = {
            'order_id': self.id,
            'name': so_description,
            'product_uom_qty': 1,
            'product_uom': carrier.product_id.uom_id.id,
            'product_id': carrier.product_id.id,
            'tax_id': [(6, 0, taxes_ids)],
            'is_delivery': True,
            'line_warehouse_id_new': SaleOrderLine_rec.line_warehouse_id_new.id,
            'delivery_address_id': SaleOrderLine_rec.delivery_address_id.id,
            'multiple_do_date_new': SaleOrderLine_rec.multiple_do_date_new,
            'account_tag_ids': SaleOrderLine_rec.account_tag_ids.ids,
        }
        if carrier.invoice_policy == 'real':
            values['price_unit'] = 0
            values['name'] += _(' (Estimated Cost: %s )', self._format_currency_amount(price_unit))
        else:
            values['price_unit'] = price_unit
        if carrier.free_over and self.currency_id.is_zero(price_unit) :
            values['name'] += '\n' + 'Free Shipping'
        if self.order_line:
            values['sequence'] = self.order_line[-1].sequence + 1
            values['sale_line_sequence'] = len(self.order_line) + 1
        sol = SaleOrderLine.sudo().create(values)
        return sol

    def get_po_values(self , company_partner_id , current_company_id):
        values = super(SaleOrder, self).get_po_values(company_partner_id, current_company_id)
        branch_id = self.env['res.branch'].sudo().search([('company_id', '=', company_partner_id.id)], limit=1)
        values['branch_id'] = branch_id.id
        values['is_goods_orders'] = any(line.product_id.type == 'product' for line in self.order_line)
        values['is_services_orders'] = any(line.product_id.type == 'service' for line in self.order_line)
        return values

    @api.onchange('sh_sale_barcode_mobile')
    def _onchange_sh_sale_barcode_mobile(self):

        if self.sh_sale_barcode_mobile in ['', "", False, None]:
            return

        CODE_SOUND_SUCCESS = ""
        CODE_SOUND_FAIL = ""
        if self.env.user.company_id.sudo().sh_sale_bm_is_sound_on_success:
            CODE_SOUND_SUCCESS = "SH_BARCODE_MOBILE_SUCCESS_"

        if self.env.user.company_id.sudo().sh_sale_bm_is_sound_on_fail:
            CODE_SOUND_FAIL = "SH_BARCODE_MOBILE_FAIL_"

        # step 1 make sure order in proper state.
        if self and self.state in ["cancel", "done"]:
            selections = self.fields_get()["state"]["selection"]
            value = next((v[1] for v in selections if v[0]
                          == self.state), self.state)

            if self.env.user.company_id.sudo().sh_sale_bm_is_notify_on_fail:
                message = _(CODE_SOUND_FAIL +
                            'You can not scan item in %s state.') % (value)
                self.env['bus.bus'].sendone(
                    (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                    {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})

            return

        # step 2 increaset product qty by 1 if product not in order line than create new order line.
        elif self:
            search_lines = False
            domain = []
            barcode_config = self.env['barcode.configuration'].search([], limit=1).barcode_type
            if self.env.user.company_id.sudo().sh_sale_barcode_mobile_type == "barcode":
                search_lines = self.order_line.filtered(
                    lambda ol: ol.product_id.barcode == self.sh_sale_barcode_mobile or ol.product_id.barcode_ean13_value == self.sh_sale_barcode_mobile)
                if barcode_config == 'EAN13':
                    domain = ['|', ("barcode_ean13_value", "=", self.sh_sale_barcode_mobile),("barcode", "=", self.sh_sale_barcode_mobile)]
                else:
                    domain = [("barcode", "=", self.sh_purchase_barcode_mobile)]


            elif self.env.user.company_id.sudo().sh_sale_barcode_mobile_type == "int_ref":
                search_lines = self.order_line.filtered(
                    lambda ol: ol.product_id.default_code == self.sh_sale_barcode_mobile)
                domain = [("default_code", "=", self.sh_sale_barcode_mobile)]

            elif self.env.user.company_id.sudo().sh_sale_barcode_mobile_type == "sh_qr_code":
                search_lines = self.order_line.filtered(
                    lambda ol: ol.product_id.sh_qr_code == self.sh_sale_barcode_mobile)
                domain = [("sh_qr_code", "=", self.sh_sale_barcode_mobile)]

            elif self.env.user.company_id.sudo().sh_sale_barcode_mobile_type == "all":
                search_lines = self.order_line.filtered(lambda ol: ol.product_id.barcode == self.sh_sale_barcode_mobile or ol.product_id.default_code ==
                                                                   self.sh_sale_barcode_mobile or ol.product_id.barcode_ean13_value == self.sh_sale_barcode_mobile or ol.product_id.sh_qr_code == self.sh_sale_barcode_mobile)
                if barcode_config == 'EAN13':
                    domain = ["|", "|", "|",
                              ("default_code", "=", self.sh_sale_barcode_mobile),
                              ("barcode", "=", self.sh_sale_barcode_mobile),
                              ("sh_qr_code", "=", self.sh_sale_barcode_mobile),
                              ("barcode_ean13_value", "=", self.sh_sale_barcode_mobile),]
                else:
                    domain = ["|", "|",
                              ("default_code", "=", self.sh_sale_barcode_mobile),
                              ("barcode", "=", self.sh_sale_barcode_mobile),
                              ("sh_qr_code", "=", self.sh_sale_barcode_mobile),
                              ]

            if search_lines:
                for line in search_lines:
                    line.product_uom_qty += 1
                    # force compute uom and prices
                    line.product_id_change()
                    line.product_uom_change()
                    line._onchange_discount()

                    if self.env.user.company_id.sudo().sh_sale_bm_is_notify_on_success:
                        message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (
                            line.product_id.name, line.product_uom_qty)
                        self.env['bus.bus'].sendone(
                            (self._cr.dbname, 'res.partner',
                             self.env.user.partner_id.id),
                            {'type': 'simple_notification', 'title': _('Succeed'), 'message': message, 'sticky': False, 'warning': False})
                    break
            else:
                search_product = self.env["product.product"].search(
                    domain, limit=1)
                if search_product:
                    vals = {
                        'product_id': search_product.id,
                        'name': search_product.name,
                        'product_uom': search_product.uom_id.id,
                        'product_uom_qty': 1,
                        'price_unit': search_product.lst_price,
                    }
                    if search_product.uom_id:
                        vals.update({
                            "product_uom": search_product.uom_id.id,
                        })

                    new_order_line = self.order_line.with_context(
                        {'default_order_id': self.id}).new(vals)
                    # force compute uom and prices
                    new_order_line.product_id_change()
                    new_order_line.product_uom_change()
                    new_order_line._onchange_discount()
                    self.order_line += new_order_line

                    if self.env.user.company_id.sudo().sh_sale_bm_is_notify_on_success:
                        message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (
                            new_order_line.product_id.name, new_order_line.product_uom_qty)
                        self.env['bus.bus'].sendone(
                            (self._cr.dbname, 'res.partner',
                             self.env.user.partner_id.id),
                            {'type': 'simple_notification', 'title': _('Succeed'), 'message': message, 'sticky': False, 'warning': False})

                else:
                    if self.env.user.company_id.sudo().sh_sale_bm_is_notify_on_fail:
                        message = _(
                            CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any product!')
                        self.env['bus.bus'].sendone(
                            (self._cr.dbname, 'res.partner',
                             self.env.user.partner_id.id),
                            {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})
    
class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model
    def create(self, vals):
        if vals.get('model') and \
            vals.get('model') == 'sale.order' and vals.get('tracking_value_ids'):
            sale_state_1 = self.env['ir.model.fields']._get('sale.order', 'sale_state_1').id
            state_2 = self.env['ir.model.fields']._get('sale.order', 'state_2').id
            approval_matrix_state = self.env['ir.model.fields']._get('sale.order', 'approval_matrix_state').id
            approval_matrix_state_1 = self.env['ir.model.fields']._get('sale.order', 'approval_matrix_state_1').id
            vals['tracking_value_ids'] = [rec for rec in vals.get('tracking_value_ids') if
                                        rec[2].get('field') not in (sale_state_1, state_2,
                                        approval_matrix_state, approval_matrix_state_1)]
        return super(MailMessage, self).create(vals)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    auto_mail = fields.Boolean(string="Automation Email")
    group_multi_do = fields.Boolean(string="Multiple Delivery Address?", implied_group='equip3_sale_operation.group_multi_do')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        res.update({
            'auto_mail': IrConfigParam.get_param('auto_mail', False),
            'group_multi_do': IrConfigParam.get_param('group_multi_do', False),
        })
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('auto_mail', self.auto_mail)
        self.env['ir.config_parameter'].sudo().set_param('group_multi_do', self.group_multi_do)

class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    def action_send_mail(self):
        context = dict(self.env.context) or {}
        if context.get('default_model') and context.get('default_res_id'):
            record = self.env[context.get('default_model')].browse([context.get('default_res_id')])
            if record._name == 'sale.order':
                if record.state != 'sale':
                    record.write({'state': 'sent'})
                record.message_post(body="Quotation Send by Email")
            elif record._name == 'purchase.order':
                if record.state != 'purchase':
                    record.write({'state': 'sent'})
                record.message_post(body="Quotation Send by Email")
        return super(MailComposer, self).action_send_mail()

class ModProductBundle(models.TransientModel):
    _inherit = 'wizard.product.bundle.bi'

    def mod_button_add_product_bundle_bi(self):
        next_num = 0
        order_line_data = self.env['sale.order.line'].search([('order_id','=', self._context['active_id'])])
        sale_data = self.env['sale.order'].search([('id', '=', self._context['active_id'])])
        if order_line_data:
            next_num = next_num + int(self.env['sale.order.line'].browse(order_line_data.ids[-1]).sale_line_sequence) + 1
        else:
            next_num += 1
        if self.bi_pack_ids:
            for pack in self.bi_pack_ids:
                sale_order_id = self.env['sale.order.line'].search([('order_id','=', self._context['active_id']),('product_id','=',pack.product_id.id)])
                if sale_order_id and  sale_order_id[0] :
                    sale_order_line_obj = sale_order_id[0]
                    sale_order_line_obj.write({'product_uom_qty': sale_order_line_obj.product_uom_qty + (pack.qty_uom * self.product_qty)})


                else:
                    self.env['sale.order.line'].create({'sale_line_sequence':str(next_num),
                                                    'order_id':self._context['active_id'],
                                                    'product_id':pack.product_id.id,
                                                    'name':pack.product_id.name,
                                                    'price_unit':pack.product_id.list_price,
                                                    'product_uom':pack.uom_id.id,
                                                    'product_uom_qty':pack.qty_uom * self.product_qty,
                                                    'multiple_do_date': sale_data.commitment_date,
                                                    'delivery_address_id': sale_data.partner_invoice_id.id,
                                                    'line_warehouse_id': sale_data.warehouse_id.id,
                                                    'account_tag_ids': sale_data.account_tag_ids.ids,
                                                    })
                    next_num += 1

        return True

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def _prepare_so_line(self, order, analytic_tag_ids, tax_ids, amount):
        res = super()._prepare_so_line(order, analytic_tag_ids, tax_ids, amount)
        if 'is_downpayment' in res:
            order.is_down_payment = True
            res['is_down_payment'] = True
            res['product_uom_qty'] = 1
        return res

    def check_dp(self):
        order_id = self.env['sale.order'].browse(self._context.get('active_ids', []))
        if self.advance_payment_method == 'percentage':
            if self.amount + order_id.down_payment_amount_percentage >= 100:
                raise ValidationError("Down payment percentage cannot be greater than 100%")
        elif self.advance_payment_method == 'fixed':
            if self.fixed_amount + order_id.down_payment_amount >= order_id.amount_total:
                raise ValidationError("Down payment amount cannot be greater than Total Amount")

    def create_invoices(self):
        is_dp = False
        if self.advance_payment_method == 'percentage' or self.advance_payment_method == 'fixed':
            is_dp = True
            self.check_dp()
        self.env.context = dict(self._context)
        self.env.context.update({'is_dp': is_dp})
        if not 'is_recurring' in self.env.context:
            res = super().create_invoices()
            sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))
            for order in sale_orders:
                pickings = self.env['stock.picking'].search([('sale_id', '=', order.id)])
                for invoice in order.invoice_ids:
                    invoice.write({'picking_ids': [(6, 0, pickings.ids)]})

            return res
        else:
            sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))
            for order in sale_orders:
                order._create_invoices(grouped=False, final=False, date=None)
                pickings = self.env['stock.picking'].search([('sale_id', '=', order.id)])
                for invoice in order.invoice_ids:
                    invoice.write({'picking_ids': [(6, 0, pickings.ids)]})

    def _create_invoice(self, order, so_line, amount):
        res = super()._create_invoice(order, so_line, amount)
        res._onchange_analytic_group()
        return res

    def _prepare_invoice_values(self, order, name, amount, so_line):
        res = super(SaleAdvancePaymentInv,self)._prepare_invoice_values(order, name, amount, so_line)
        if self.env.context['is_dp']:
            res['is_dp'] = True
        res['branch_id'] = order.branch_id.id
        return res

    def _get_advance_details(self, order):
        res = super()._get_advance_details(order)
        if order.recurring_invoices:
            context = {'lang': order.partner_id.lang}
            if self.advance_payment_method == 'percentage':
                if all(self.product_id.taxes_id.mapped('price_include')):
                    amount = (order.amount_total - (sum(order.order_line.filtered(lambda x: x.is_recurring).mapped('price_subtotal')))) * self.amount / 100
                else:
                    amount = (order.amount_untaxed  - (sum(order.order_line.filtered(lambda x: x.is_recurring).mapped('price_subtotal')))) * self.amount / 100
                name = _("Down payment of %s%%") % (self.amount)
            else:
                amount = self.fixed_amount
                name = _('Down Payment')
            del context
            return amount, name
        return res
