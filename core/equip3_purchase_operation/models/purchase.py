# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, SUPERUSER_ID, tools, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from odoo.http import request
from collections import defaultdict
import logging
_logger = logging.getLogger(__name__)

class PmpsAdvWizard(models.TransientModel):
    _inherit = "pmps.adv.wizard"

    def show_all_products(self):
        for res in self:
            order_id = self.env['purchase.order'].browse(self.env.context.get('sh_pmps_adv_po_id'))
            if order_id.is_services_orders:
                product_ids = self.env['product.product'].search([('type', '=', 'service')])
            elif order_id.is_assets_orders:
                product_ids = self.env['product.product'].search([('type', '=', 'asset')])
            elif order_id.is_goods_orders:
                product_ids = self.env['product.product'].search([('type', 'in', ('consu','product'))])
            else:
                product_ids = self.env['product.product'].search([])
            product_ids = product_ids.filtered(lambda r: r.company_id.id == self.env.company.id)
            if product_ids:
                lines = []
                for product_id in product_ids:
                    val = {
                        'product_id': product_id.id,
                    }
                    lines.append((0, 0, val))
                    res.product_ids = False
                res.product_ids = lines
            return {
                'name': 'Select Products Advance',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'pmps.adv.wizard',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'res_id': res.id,
                'target': 'new',
            }

    def sh_pmps_adv_select_btn(self):
        if(
                self and
                self.product_ids and
                self.env.context.get('sh_pmps_adv_po_id', False)
        ):
            for data in self:
                order_id = self.env.context.get('sh_pmps_adv_po_id')
                purchase_order_line_obj = self.env['purchase.order.line']
                purchase_id = self.env['purchase.order'].browse(order_id)
                date_planned = datetime.now()
                if purchase_id.is_delivery_receipt:
                    date_planned = purchase_id.date_planned
                for rec in data.product_ids:
                    if rec.uom_po_id:
                        created_pol = purchase_order_line_obj.create({
                            'product_id': rec.product_id.id,
                            'name': rec.product_id.name,
                            'order_id': order_id,
                            'product_qty': rec.qty,
                            'date_planned': date_planned,
                            'price_unit': rec.standard_price,
                            'product_uom': rec.uom_po_id.id,
                        })
                        if created_pol:
                            created_pol.onchange_product_id()
                            created_pol.write({'product_qty': rec.qty})

    def sh_pmps_adv_select_specific_btn(self):
        if(
                self and
                self.specific_product_ids and
                self.env.context.get('sh_pmps_adv_po_id',False)
        ):
            for data in self:
                order_id = self.env.context.get('sh_pmps_adv_po_id')
                purchase_order_line_obj = self.env['purchase.order.line']
                purchase_id = self.env['purchase.order'].browse(order_id)
                date_planned = datetime.now()
                if purchase_id.is_delivery_receipt:
                    date_planned = purchase_id.date_planned
                for rec in data.specific_product_ids:
                    if rec.uom_po_id:
                        created_pol = purchase_order_line_obj.create({
                            'product_id': rec.product_id.id,
                            'name': rec.product_id.name,
                            'order_id': order_id,
                            'product_qty': rec.qty,
                            'date_planned': date_planned,
                            'price_unit': rec.standard_price,
                            'product_uom': rec.uom_po_id.id,
                        })
                        if created_pol:
                            created_pol.onchange_product_id()
                            created_pol.write({'product_qty': rec.qty})

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # def write(self, vals):
    #     res = super(PurchaseOrder, self).write(vals)
    #     for line in self.order_line:
    #         if self.analytic_account_group_ids != line.analytic_tag_ids:
    #             line.update({
    #                 'analytic_tag_ids': [(6, 0, self.analytic_account_group_ids.ids)],
    #             })
    #     return res

    term_condition = fields.Many2one('term.condition', string="Terms and Conditions: ")
    term_condition_box = fields.Html("Terms and Conditions")
    bo_count = fields.Integer(
        string="Blanket Order",
        compute="_compute_purchase_bo_count",
        readonly=True,
    )
    blanket_ids = fields.One2many('purchase.requisition','purchase_id', string="Blanket Orders")
    multilevel_disc = fields.Boolean(string="Multi Level Discount", compute="_compute_multilevel_disc")
    multi_discount = fields.Char('Multi Discount')
    vendor_payment_terms = fields.Char(string="Vendor Payment Terms", default=" ")
    service_level_agreement_id = fields.Many2one('service.level.agreement', string="Service Level Agreement")
    service_level_agreement_box = fields.Html("Agreement")
    user_request_ids = fields.Many2many('res.users', string="User Purchase Request")
    vendor_invoice_documents_count = fields.Integer(string='Vendor Invoice Documents Count', compute='_compute_vendor_invoice_documents_count')
    down_payment_discount_amount = fields.Float()
    res_sh_purchase_barcode_mobile = fields.Char(string="Mobile Barcode")
    is_backorder = fields.Boolean("Backorder")

    @api.onchange('currency_id')
    def convert_price_unit(self):
        for rec in self:
            for line in rec.order_line:
                if rec.currency_id != line.res_currency_id:
                    line.price_unit = line.res_currency_id._convert(line.price_unit, rec.currency_id, line.company_id, fields.Date.context_today(self))
                    line.res_currency_id = rec.currency_id.id

    @api.onchange('res_sh_purchase_barcode_mobile')
    def onchange_res_sh_purchase_barcode_mobile(self):
        for rec in self:
            rec.sh_purchase_barcode_mobile = rec.res_sh_purchase_barcode_mobile

    @api.onchange('sh_purchase_barcode_mobile')
    def _onchange_sh_purchase_barcode_mobile(self):

        if self.sh_purchase_barcode_mobile in ['', "", False, None]:
            return

        CODE_SOUND_SUCCESS = ""
        CODE_SOUND_FAIL = ""
        if self.env.user.company_id.sudo().sh_purchase_bm_is_sound_on_success:
            CODE_SOUND_SUCCESS = "SH_BARCODE_MOBILE_SUCCESS_"

        if self.env.user.company_id.sudo().sh_purchase_bm_is_sound_on_fail:
            CODE_SOUND_FAIL = "SH_BARCODE_MOBILE_FAIL_"

        # step 1 make sure order in proper state.
        if self and self.state in ["cancel", "done"]:
            selections = self.fields_get()["state"]["selection"]
            value = next((v[1] for v in selections if v[0]
                          == self.state), self.state)

            if self.env.user.company_id.sudo().sh_purchase_bm_is_notify_on_fail:
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
            if self.env.user.company_id.sudo().sh_purchase_barcode_mobile_type == "barcode":
                search_lines = self.order_line.filtered(
                    lambda ol: ol.product_id.barcode == self.sh_purchase_barcode_mobile or ol.product_id.barcode_ean13_value == self.sh_purchase_barcode_mobile)
                if barcode_config == 'EAN13':
                    domain = ['|', ("barcode_ean13_value", "=", self.sh_purchase_barcode_mobile),("barcode", "=", self.sh_purchase_barcode_mobile)]
                else:
                    domain = [("barcode", "=", self.sh_purchase_barcode_mobile)]

            elif self.env.user.company_id.sudo().sh_purchase_barcode_mobile_type == "int_ref":
                search_lines = self.order_line.filtered(
                    lambda ol: ol.product_id.default_code == self.sh_purchase_barcode_mobile)
                domain = [
                    ("default_code", "=", self.sh_purchase_barcode_mobile)]

            elif self.env.user.company_id.sudo().sh_purchase_barcode_mobile_type == "sh_qr_code":
                search_lines = self.order_line.filtered(
                    lambda ol: ol.product_id.sh_qr_code == self.sh_purchase_barcode_mobile)
                domain = [("sh_qr_code", "=", self.sh_purchase_barcode_mobile)]

            elif self.env.user.company_id.sudo().sh_purchase_barcode_mobile_type == "all":
                search_lines = self.order_line.filtered(lambda ol: ol.product_id.barcode == self.sh_purchase_barcode_mobile
                                                                   or ol.product_id.default_code == self.sh_purchase_barcode_mobile
                                                                   or ol.product_id.barcode_ean13_value == self.sh_purchase_barcode_mobile
                                                                   or ol.product_id.sh_qr_code == self.sh_purchase_barcode_mobile
                                                        )
                if barcode_config == 'EAN13':
                    domain = ["|", "|", "|",
                              ("default_code", "=", self.sh_purchase_barcode_mobile),
                              ("barcode", "=", self.sh_purchase_barcode_mobile),
                              ("sh_qr_code", "=", self.sh_purchase_barcode_mobile),
                              ("barcode_ean13_value", "=", self.sh_purchase_barcode_mobile),]
                else:
                    domain = ["|", "|",
                              ("default_code", "=", self.sh_purchase_barcode_mobile),
                              ("barcode", "=", self.sh_purchase_barcode_mobile),
                              ("sh_qr_code", "=", self.sh_purchase_barcode_mobile)]

            if search_lines:
                for line in search_lines:
                    line.product_qty = line.product_qty + 1

                    if self.env.user.company_id.sudo().sh_purchase_bm_is_notify_on_success:
                        message = _(
                            CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (line.product_id.name, line.product_qty)
                        self.env['bus.bus'].sendone(
                            (self._cr.dbname, 'res.partner',
                             self.env.user.partner_id.id),
                            {'type': 'simple_notification', 'title': _('Succeed'), 'message': message, 'sticky': False, 'warning': False})
                    break

            else:
                search_product = self.env["product.product"].search(
                    domain, limit=1)
                if search_product:

                    order_line_val = {
                        "name": search_product.name,
                        "product_id": search_product.id,
                        "product_qty": 1,
                        "price_unit": search_product.lst_price,
                        "date_planned": str(fields.Date.today())
                    }
                    if search_product.uom_id:
                        order_line_val.update({
                            "product_uom": search_product.uom_po_id.id,
                        })

                    new_order_line = self.order_line.new(order_line_val)
                    self.order_line += new_order_line
                    new_order_line.onchange_product_id()

                    if self.env.user.company_id.sudo().sh_purchase_bm_is_notify_on_success:
                        message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (
                            new_order_line.product_id.name, new_order_line.product_qty)
                        self.env['bus.bus'].sendone(
                            (self._cr.dbname, 'res.partner',
                             self.env.user.partner_id.id),
                            {'type': 'simple_notification', 'title': _('Succeed'), 'message': message, 'sticky': False, 'warning': False})

                else:
                    if self.env.user.company_id.sudo().sh_purchase_bm_is_notify_on_fail:
                        message = _(
                            CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any product!')
                        self.env['bus.bus'].sendone(
                            (self._cr.dbname, 'res.partner',
                             self.env.user.partner_id.id),
                            {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})

    def copy(self, default=None):
        self.env.context = dict(self._context)
        self.env.context.update({'from_duplicate': True})
        res = super(PurchaseOrder, self).copy(default)
        return res

    @api.model
    def create(self, vals):
        if 'from_duplicate' not in self.env.context:
            self.check_existing_line(vals)
        return super(PurchaseOrder, self).create(vals)

    def write(self, vals):
        res = super(PurchaseOrder, self).write(vals)
        if 'order_line' in vals:
            self.check_existing_order_line()
        return res

    def check_existing_order_line(self):
        for rec in self:
            existing_products = {}
            merge_lines = {}
            new_lines = []
            for line in rec.order_line:
                if line.display_type:
                    new_lines.append(line.id)
                    continue
                id = line.id
                product_id = line.product_id.id
                name = line.name
                destination_warehouse_id = line.destination_warehouse_id.id
                quantity = line.product_qty
                date_planned = line.date_planned
                analytic_tag_ids = ','.join(str(x) for x in line.analytic_tag_ids.ids)
                discount_method = line.discount_method
                discount_amount = line.discount_amount
                product_uom = line.product_uom
                price_unit = line.price_unit
                taxes_id = ','.join(str(x) for x in line.taxes_id.ids)

                key = (product_id, name, destination_warehouse_id, date_planned, analytic_tag_ids, discount_method, discount_amount, product_uom, price_unit,taxes_id)
                if key in existing_products:
                    existing_products[key] += quantity
                else:
                    existing_products[key] = quantity
                    new_lines.append(id)
            merge_lines = list(set(rec.order_line.ids) - set(new_lines))
            if merge_lines:
                self.env['purchase.order.line'].browse(merge_lines).unlink()
            i = 0
            for key, quantity in existing_products.items():
                po_line_id = self.env['purchase.order.line'].browse(new_lines[i])
                if not po_line_id.display_type:
                    po_line_id.write({'product_qty': quantity})
                i += 1

    def check_existing_line(self, vals):
        existing_products = {}
        list_sequence = []
        is_section_note = False
        new_order_lines = []
        for line in vals.get('order_line', []):
            if line[2]['display_type'] if 'display_type' in line[2] else False:
                new_order_lines.append((0, 0, line[2]))
                continue
            sequence = line[2]['sequence'] if 'sequence' in line[2] else False
            product_id = line[2]['product_id'] if 'product_id' in line[2] else False
            name = line[2]['name'] if 'name' in line[2] else False
            destination_warehouse_id = line[2]['destination_warehouse_id'] if 'destination_warehouse_id' in line[2] else False
            quantity = line[2]['product_qty'] if 'product_qty' in line[2] else False
            date_planned = line[2]['date_planned'] if 'date_planned' in line[2] else False
            analytic_tag_ids = ','.join(str(x) for x in line[2]['analytic_tag_ids'][0][2]) if 'analytic_tag_ids' in line[2] else False
            discount_method = line[2]['discount_method'] if 'discount_method' in line[2] else False
            discount_amount = line[2]['discount_amount'] if 'discount_amount' in line[2] else False
            product_uom = line[2]['product_uom'] if 'product_uom' in line[2] else False
            price_unit = line[2]['price_unit'] if 'price_unit' in line[2] else False
            taxes_id = ','.join(str(x) for x in line[2]['taxes_id'][0][2]) if 'taxes_id' in line[2] else False

            key = (product_id, name, destination_warehouse_id, date_planned, analytic_tag_ids, discount_method, discount_amount, product_uom, price_unit,taxes_id)
            if key in existing_products:
                existing_products[key] += quantity
            else:
                existing_products[key] = quantity
                list_sequence.append(sequence)
        i = 0
        for key, quantity in existing_products.items():
            product_id, name, destination_warehouse_id, date_planned, analytic_tag_ids, discount_method, discount_amount, product_uom, price_unit,taxes_id = key
            new_order_lines.append((0, 0, {
                'sequence': list_sequence[i],
                'product_id': product_id,
                'name': name,
                'destination_warehouse_id': destination_warehouse_id,
                'product_qty': quantity,
                'date_planned': date_planned,
                'analytic_tag_ids': [int(analytic_tag_id) for analytic_tag_id in analytic_tag_ids.split(',')] if analytic_tag_ids else [],
                'discount_method': discount_method,
                'discount_amount': discount_amount,
                'product_uom': product_uom,
                'price_unit': price_unit,
                'taxes_id': [int(tax_id) for tax_id in taxes_id.split(',')] if taxes_id else [],
            }))
            i += 1
        vals['order_line'] = new_order_lines

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = dict(self.env.context) or {}
        domain.extend(['|',('branch_id', '=', False), ('branch_id', 'in', self.env.branches.ids)])
        return super().read_group(domain, fields, groupby, offset=offset, limit=limit,orderby=orderby, lazy=lazy)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        domain.extend(['|',('branch_id', '=', False), ('branch_id', 'in', self.env.branches.ids)])
        return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        # DP line pake disc ????
        # res['branch_id'] = self.branch_id.id
        # context = dict(self.env.context) or {}
        # down_payment_line = self.order_line.filtered(lambda l: l.is_down_payment)
        # if down_payment_line:
        #     discount_amount = 0.0
        #     if self.discount_method == 'per':
        #         discount_amount = (self.amount_untaxed * self.discount_amount) / 100
        #     elif self.discount_method == 'fix':
        #         discount_amount = self.discount_amount
        #     amount_untaxed = self.amount_untaxed - discount_amount
        #
        #     if context.get('down_payment_by') == 'percentage':
        #         price_unit = round((amount_untaxed * context.get('amount', 0.0)) / 100, 2)
        #         self.write({
        #             'down_payment_discount_amount': round((self.amount_untaxed * context.get('amount', 0.0)) / 100, 2),
        #             'order_line': [(1, down_payment_line.id, {'price_unit': price_unit})]
        #         })
        #     elif context.get('down_payment_by') == 'fixed':
        #         price_unit = context.get('amount', 0.0)
        #         self.write({
        #             'down_payment_discount_amount': context.get('amount', 0.0),
        #             'order_line': [(1, down_payment_line.id, {'price_unit': price_unit})]
        #         })
        return res

    def _compute_vendor_invoice_documents_count(self):
        for rec in self:
            doc = self.env['ir.attachment'].sudo().search_count(
                [('res_id', '=', rec.id), ('res_model', '=', rec._name), ('sh_is_publish_in_portal', '=', True)])
            rec.vendor_invoice_documents_count = doc

    def _compute_document_count(self):
        for rec in self:
            doc = self.env['ir.attachment'].search_count(
                [('res_id', '=', rec.id), ('res_model', '=', rec._name), ('sh_is_publish_in_portal', '=', False)])
            rec.document_count = doc

    def sh_pmps_adv_btn(self):
        res = super(PurchaseOrder, self).sh_pmps_adv_btn()
        view_id = self.env['ir.ui.view'].browse([res['view_id']])
        arch = view_id.arch.split("<button name='filter_products' string='Filter Products' type='object'/>")
        arch[0] = arch[0] + "<button name='show_all_products' string='Show All Products' type='object'/><button name='filter_products' string='Filter Products' type='object'/>"
        arch = arch[0]+arch[1]
        view_id.arch = arch
        return res

    def get_disocunt(self, percentage, amount):
        new_amount = (percentage * amount) / 100
        return (amount - new_amount)

    @api.onchange('multi_discount')
    def _onchange_multi_discount(self):
        if self.multi_discount:
            amount = 100
            splited_discounts = self.multi_discount.split("+")
            for disocunt in splited_discounts:
                try:
                    amount = self.get_disocunt(float(disocunt), amount)
                except ValueError:
                    raise ValidationError("Please Enter Valid Multi Discount")     
            if amount < 0:
                raise ValidationError("Please Enter Valid Multi Discount")
            else:
                self.discount_amount = 100 - amount
        else:
            self.discount_amount = 0

    @api.onchange('discount_type')
    def reset_discount(self):
        for res in self:
            res.reset_disc()
            for line in res.order_line:
                line.reset_disc()

    @api.onchange('discount_method')
    def reset_disc(self):
        for res in self:
            res.discount_amount = 0
            res.multi_discount = '0'

    @api.onchange('discount_amount', 'multi_discount')
    # @api.onchange('discount_type', 'discount_amount', 'multi_discount', 'discount_method')
    def _set_discount_line(self):
        for res in self:
            if res.discount_amount:
                for line in res.order_line:
                    line.discount_amount = res.discount_amount
                    line.discount_method = res.discount_method
                    if res.multilevel_disc:
                        line.multi_discount = res.multi_discount

    @api.depends("state")
    def _compute_multilevel_disc(self):
        for res in self:
            res.multilevel_disc = self.env['ir.config_parameter'].sudo().get_param('multilevel_disc')
            # res.multilevel_disc = self.env.company.multilevel_disc

    @api.depends("blanket_ids")
    def _compute_purchase_bo_count(self):
        for record in self:
            record.bo_count = len(record.blanket_ids)

    def action_view_purchase_bo(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Blanket Order',
            'view_mode': 'tree,form',
            'res_model': 'purchase.requisition',
            'domain': [('purchase_id', '=', self.id)],
            'target': 'current'
        }

    # @api.depends('term_condition')
    # def _compute_term_condition_box(self):
    #     for res in self:
    #         if res.term_condition:
    #             res.term_condition_box = res.term_condition.term_condition
    #             res.notes = res.term_condition.term_condition
    #         else:
    #             res.term_condition_box = False
    #             res.notes = False

    @api.onchange('service_level_agreement_id')
    def _set_service_level_agreement_box(self):
        for res in self:
            if res.service_level_agreement_id:
                res.service_level_agreement_box = res.service_level_agreement_id.term_condition
            else:
                res.service_level_agreement_box = False

    @api.onchange('term_condition')
    def _set_term_condition_box(self):
        for res in self:
            if res.term_condition:
                res.term_condition_box = res.term_condition.term_condition
                res.notes = res.term_condition.term_condition
            else:
                res.term_condition_box = False
                res.notes = False

    @api.onchange('term_condition_box')
    def _set_notes(self):
        for res in self:
            res.notes = res.term_condition_box

    @api.depends("order_line.qty_received")
    def _compute_shipment(self):
        res = super(PurchaseOrder, self)._compute_shipment()
        context = dict(self.env.context) or {}
        for record in self:
            record.sh_hidden_compute_field = False
        return res

    @api.onchange('analytic_account_group_ids')
    def set_analytic_group(self):
        for res in self:
            for line in res.order_line:
                line.update({
                    'analytic_tag_ids': [(6, 0, res.analytic_account_group_ids.ids)],
                })

    @api.onchange('discount_type', 'discount_method', 'discount_amount')
    def set_disc(self):
        for res in self:
            if res.discount_type == 'global':
                gross_total = discount_amount = 0
                gross_total = sum(res.order_line.mapped('gross_total'))
                # for line_gross in res.order_line:
                #     gross_total += line_gross.product_uom_qty * line_gross.price_unit

                for line in res.order_line:
                    if res.discount_type == 'global':
                        if res.discount_method == 'fix':
                            if gross_total > 0:
                                discount_amount = (res.discount_amount / gross_total) * (
                                        line.product_uom_qty * line.price_unit)
                        else:
                            discount_amount = res.discount_amount
                    else:
                        discount_amount = res.discount_amount

                    line.update({
                        'discount_method': res.discount_method,
                        'discount_amount': discount_amount
                    })

    def print_quotation(self):
        return self.env.ref('general_template.report_purchase_exclusive').report_action(self)

    def _create_stock_moves(self, picking):
        res = super(PurchaseOrder, self)._create_stock_moves(picking)
        return res

    def _get_destination_location(self):
        res = super()._get_destination_location()
        if self.env.context.get('picking_type_id'):
            res = self.env.context.get('picking_type_id').default_location_dest_id.id
        return res

    @api.model
    def _prepare_picking(self):
        res = super(PurchaseOrder, self)._prepare_picking()
        res.update({
            'branch_id': self.env.context.get('branch_id') or self.branch_id.id,
            'analytic_account_group_ids': [(6, 0, self.analytic_account_group_ids.ids)],
        })
        return res

    def action_view_invoice(self, invoices=False):
        # fix issue analytic journal item tax
        if invoices:
            invoices._onchange_analytic_group()
        # fix issue invoice direct purchase
        # confirm direct purchase lgsg buat inv tp invoice_ids selalu kosong walaupun computenya jalan
        for order in self:
            if len(order.invoice_ids) != order.invoice_count:
                order.invoice_ids = order.mapped('order_line.invoice_lines.move_id')
        res = super().action_view_invoice(invoices)
        return res
    #     """ copy this function from bi_sale_purchase_discount_with_tax module
    #     and comment out to update amount related fields

    #     This function returns an action that display existing vendor bills of
    #     given purchase order ids. When only one found, show the vendor bill
    #     immediately.
    #     """
    #     if not invoices:
    #         # somehow _compute_invoice is not triggered
    #         self._compute_invoice()

    #         # Invoice_ids may be filtered depending on the user. To ensure we get all
    #         # invoices related to the purchase order, we read them in sudo to fill the
    #         # cache.
    #         self._compute_invoice()
    #         self.sudo()._read(['invoice_ids'])
    #         invoices = self.invoice_ids

    #     action = self.env.ref('account.action_move_in_invoice_type').sudo()
    #     result = action.read()[0]
    #     # invoices.write({
    #     #     'discount_method': self.discount_method,
    #     #     'discount_amt': self.discount_amt,
    #     #     'discount_amount': self.discount_amount,
    #     #     'discount_type': self.discount_type,
    #     #     'discount_amt_line': self.discount_amt_line,
    #     #     'amount_untaxed': self.amount_untaxed,
    #     #     'amount_total': self.amount_total,
    #     # })

    #     # choose the view_mode accordingly
    #     if len(invoices) > 1:
    #         result['domain'] = [('id', 'in', invoices.ids)]
    #     elif len(invoices) == 1:
    #         res = self.env.ref('account.view_move_form', False)
    #         form_view = [(res and res.id or False, 'form')]
    #         if 'views' in result:
    #             result['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
    #         else:
    #             result['views'] = form_view
    #         result['res_id'] = invoices.id
    #     else:
    #         result = {'type': 'ir.actions.act_window_close'}
    #     return result

    def open_document(self):
        if self:
            document = self.env['ir.attachment'].search(
                [('res_id', '=', self.id), ('res_model', '=', self._name), ('sh_is_publish_in_portal', '=', False)])
            action = self.env.ref(
                'base.action_attachment').sudo().read()[0]
            action['context'] = {'domain': [('id', 'in', document.ids)], 'search_default_res_id': self.id,
                                 'default_res_id': self.id, 'default_res_model': self._name, }
            action['domain'] = [('id', 'in', document.ids)]
            return action

    def action_vendor_invoice_documents(self):
        if self:
            document = self.env['ir.attachment'].sudo().search(
                [('res_id', '=', self.id), ('res_model', '=', self._name), ('sh_is_publish_in_portal', '=', True)])
            action = self.env.ref(
                'base.action_attachment').sudo().read()[0]
            action['context'] = {'domain': [('id', 'in', document.ids)], 'search_default_res_id': self.id,
                                 'default_res_id': self.id, 'default_res_model': self._name, 'default_sh_is_publish_in_portal': True}
            action['domain'] = [('id', 'in', document.ids)]
            return action

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    state_delivery = fields.Selection([
        ('nothing', 'Nothing'),
        ('draft', 'New'), ('cancel', 'Cancelled'),
        ('waiting', 'Waiting Another Move'),
        ('confirmed', 'Waiting Availability'),
        ('partially_available', 'Partially Available'),
        ('assigned', 'Available'),
        ('done', 'Done')], string='Status Delivery',
        copy=False, default='nothing', index=True, readonly=True,
        help="* New: When the stock move is created and not yet confirmed.\n"
             "* Waiting Another Move: This state can be seen when a move is waiting for another one, for example in a chained flow.\n"
             "* Waiting Availability: This state is reached when the procurement resolution is not straight forward. It may need the scheduler to run, a component to be manufactured...\n"
             "* Available: When products are reserved, it is set to \'Available\'.\n"
             "* Done: When the shipment is processed, the state is \'Done\'.")

    state_inv = fields.Selection(selection=[
        ('nothing', 'Nothing'),
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
    ], string='Status Invoice', default='nothing')

    multi_discount = fields.Char('Multi Discount')
    product_type = fields.Selection(related='product_id.type')
    virtual_available_at_date = fields.Float(compute='_compute_qty_at_date', digits='Product Unit of Measure', store=True) #dijadikan store true karena nilai nya berubah ketika ada perubahan pada state dan beberapa field lain yg sudah didepends
    scheduled_date = fields.Datetime(compute='_compute_qty_at_date', store=True)
    forecast_expected_date = fields.Datetime(compute='_compute_qty_at_date', store=True)
    free_qty_today = fields.Float(compute='_compute_qty_at_date', digits='Product Unit of Measure', store=True)
    qty_available_today = fields.Float(compute='_compute_qty_at_date', store=True)
    qty_to_deliver = fields.Float(compute='_compute_qty_to_deliver', digits='Product Unit of Measure', store=True) #dijadikan store true karena nilai emmang akan berubah ketika barang diterima berubah (sudah ada depend move_ids), sehingga tidak perlu di cek setiap saat
    is_mto = fields.Boolean(compute='_compute_is_mto', store=True)
    display_qty_widget = fields.Boolean(compute='_compute_qty_to_deliver', store=True)
    route_id = fields.Many2one('stock.location.route', string='Route', ondelete='restrict', check_company=True)
    # kenapa computenya diilangin (?)
    # reference_purchase_price = fields.Float(string='Reference Price', compute="")
    # purchase_line_cost_saving = fields.Float(string='Cost Savings', compute="")
    # total_cost_saving = fields.Float(string='Total Cost Savings', compute="")
    # cost_saving_percentage = fields.Float(string='Cost Savings (%)', compute="")
    # last_customer_purchase_price = fields.Float(string="Last Purchase Price Of Vendor", compute='')
    # current_qty = fields.Float(string="Current Qty in Warehouse", compute="")
    # incoming_stock = fields.Float(string="Incoming Stock", compute="")
    analytic_tag_ids = fields.Many2many('account.analytic.tag', store=True, string='Analytic Tags', compute='_compute_analytic_id_and_tag_ids', readonly=False)
    res_currency_id = fields.Many2one('res.currency')

    @api.model
    def create(self, vals):
        if self.env.context.get('list_date_planned_line'):
            vals['date_planned'] = self.env.context.get('list_date_planned_line').pop(0)
        if self.env.context.get('list_dest_warehouse_line'):
            vals['destination_warehouse_id'] = self.env.context.get('list_dest_warehouse_line').pop(0)
        if vals.get('order_id'):
            vals['res_currency_id'] = self.env['purchase.order'].browse(vals.get('order_id')).currency_id.id or False
        res = super().create(vals)
        # Somehow, there is an issue where `date_planned` is false even though it has a value in `vals`; however, during creation, it sometimes becomes false.
        if not res.date_planned:
            res.date_planned = vals['date_planned']
        return res

    @api.onchange('currency_id')
    def convert_price_unit(self):
        for rec in self:
            rec.res_currency_id = rec.currency_id

    @api.depends('product_id', 'date_order')
    def _compute_analytic_id_and_tag_ids(self):
        for rec in self:
            default_analytic_account = rec.env['account.analytic.default'].sudo().account_get(
                product_id=rec.product_id.id,
                partner_id=rec.order_id.partner_id.id,
                user_id=rec.env.uid,
                date=rec.date_order,
                company_id=rec.company_id.id,
            )
            rec.account_analytic_id = rec.account_analytic_id or default_analytic_account.analytic_id
            rec.analytic_tag_ids = rec.analytic_tag_ids or default_analytic_account.analytic_tag_ids or rec.order_id.analytic_account_group_ids.ids

    def _expected_date(self):
        self.ensure_one()
        order_date = fields.Datetime.from_string(self.order_id.date_order if self.order_id.date_order and self.order_id.state in ['purchase', 'done'] else fields.Datetime.now())
        return order_date

    @api.depends('product_type', 'product_uom_qty', 'qty_received', 'state', 'move_ids', 'product_uom')
    def _compute_qty_to_deliver(self):
        """Compute the visibility of the inventory widget."""
        for line in self:
            line.qty_to_deliver = line.product_uom_qty - line.qty_received
            if line.state in ('draft', 'purchase') and line.product_type == 'product' and line.product_uom and line.qty_to_deliver > 0:
                if line.state == 'purchase' and not line.move_ids:
                    line.display_qty_widget = False
                else:
                    line.display_qty_widget = True
            else:
                line.display_qty_widget = False

    @api.depends(
        'product_id', 'product_uom_qty', 'product_uom', 'order_id.date_planned',
        'move_ids', 'move_ids.forecast_expected_date', 'move_ids.forecast_availability')
    def _compute_qty_at_date(self):
        """ Compute the quantity forecasted of product at delivery date. There are
        two cases:
         1. The quotation has a date_planned, we take it as delivery date
         2. The quotation hasn't date_planned, we compute the estimated delivery
            date based on lead time"""
        treated = self.browse()
        for line in self.filtered(lambda l: l.state == 'purchase'):
            if not line.display_qty_widget:
                continue
            moves = line.move_ids.filtered(lambda m: m.product_id == line.product_id)
            line.forecast_expected_date = max(moves.filtered("forecast_expected_date").mapped("forecast_expected_date"), default=False)
            line.qty_available_today = 0
            line.free_qty_today = 0
            for move in moves:
                line.qty_available_today += move.product_uom._compute_quantity(move.reserved_availability, line.product_uom)
                line.free_qty_today += move.product_uom._compute_quantity(move.forecast_availability, line.product_uom)
            line.scheduled_date = line.order_id.date_planned or line._expected_date()
            line.virtual_available_at_date = False
            treated |= line

        qty_processed_per_product = defaultdict(lambda: 0)
        grouped_lines = defaultdict(lambda: self.env['purchase.order.line'])
        # We first loop over the SO lines to group them by warehouse and schedule
        # date in order to batch the read of the quantities computed field.
        for line in self.filtered(lambda l: l.state == 'draft'):
            if not (line.product_id and line.display_qty_widget):
                continue
            grouped_lines[(line.destination_warehouse_id.id, line.order_id.date_planned or line._expected_date())] |= line

        for (warehouse, scheduled_date), lines in grouped_lines.items():
            product_qties = lines.mapped('product_id').with_context(to_date=scheduled_date, warehouse=warehouse).read([
                'qty_available',
                'free_qty',
                'virtual_available',
            ])
            qties_per_product = {
                product['id']: (product['qty_available'], product['free_qty'], product['virtual_available'])
                for product in product_qties
            }
            for line in lines:
                line.scheduled_date = scheduled_date
                qty_available_today, free_qty_today, virtual_available_at_date = qties_per_product[line.product_id.id]
                line.qty_available_today = qty_available_today - qty_processed_per_product[line.product_id.id]
                line.free_qty_today = free_qty_today - qty_processed_per_product[line.product_id.id]
                line.virtual_available_at_date = virtual_available_at_date - qty_processed_per_product[line.product_id.id]
                line.forecast_expected_date = False
                product_qty = line.product_uom_qty
                if line.product_uom and line.product_id.uom_po_id and line.product_uom != line.product_id.uom_po_id:
                    line.qty_available_today = line.product_uom._compute_quantity(line.qty_available_today, line.product_uom)
                    line.free_qty_today = line.product_uom._compute_quantity(line.free_qty_today, line.product_uom)
                    line.virtual_available_at_date = line.product_uom._compute_quantity(line.virtual_available_at_date, line.product_uom)
                    product_qty = line.product_uom._compute_quantity(product_qty, line.product_uom)
                qty_processed_per_product[line.product_id.id] += product_qty
            treated |= lines
        remaining = (self - treated)
        remaining.virtual_available_at_date = False
        remaining.scheduled_date = False
        remaining.forecast_expected_date = False
        remaining.free_qty_today = False
        remaining.qty_available_today = False

    @api.depends('product_id', 'route_id', 'destination_warehouse_id', 'product_id.route_ids')
    def _compute_is_mto(self):
        """ Verify the route of the product based on the warehouse
            set 'is_available' at True if the product availibility in stock does
            not need to be verified, which is the case in MTO, Cross-Dock or Drop-Shipping
        """
        self.is_mto = False
        res = self.filtered(lambda x: x.destination_warehouse_id.mto_pull_id and x.display_qty_widget)
        if res:
            for line in res:
                # if not line.display_qty_widget:
                #     continue
                product = line.product_id
                product_routes = line.route_id or (product.route_ids + product.categ_id.total_route_ids)

                # Check MTO
                mto_route = line.destination_warehouse_id.mto_pull_id.route_id
                if not mto_route:
                    try:
                        mto_route = self.env['stock.warehouse']._find_global_route('stock.route_warehouse0_mto', _('Make To Order'))
                    except UserError:
                        # if route MTO not found in ir_model_data, we treat the product as in MTS
                        pass

                if mto_route and mto_route in product_routes:
                    line.is_mto = True
                else:
                    line.is_mto = False
        else:
            self.is_mto = False

    def get_disocunt(self, percentage, amount):
        new_amount = (percentage * amount) / 100
        return (amount - new_amount)

    @api.onchange('multi_discount')
    def _onchange_multi_discount(self):
        if self.multi_discount:
            amount = 100
            splited_discounts = self.multi_discount.split("+")
            for disocunt in splited_discounts:
                try:
                    amount = self.get_disocunt(float(disocunt), amount)
                except ValueError:
                    raise ValidationError("Please Enter Valid Multi Discount")
            self.discount_amount = 100 - amount
        else:
            self.discount_amount = 0

    @api.onchange('product_qty')
    def set_default_multi_disc(self):
        for res in self:
            if not res.is_reward_line:
                if res.order_id.discount_type == 'global':
                    res.discount_method = res.order_id.discount_method
                    res.discount_amount = res.order_id.discount_amount
                    if res.order_id.multilevel_disc:
                        res.multi_discount = res.order_id.multi_discount

    @api.constrains('qty_received')
    def set_state_delivery(self):
        for res in self:
            state = False
            # date_received = None
            if res.move_ids:
                state = res.move_ids[-1].state
            # for move in res.move_ids:
            #     state = move.state
                # date_received = move.date_done
            if state:
                res.state_delivery = state
            # if date_received:
            #     res.date_received = date_received

    @api.constrains('qty_invoiced')
    def set_state_inv(self):
        pass
        # for res in self:
        #     state = ''
        #     # for inv in res.invoice_lines:
        #     #     state = inv.state
        #     if state:
        #         res.state_inv = state

    @api.onchange('destination_warehouse_id')
    def set_dest(self):
        for res in self:
            res.picking_type_id = False
            if res.order_id.is_single_delivery_destination:
                res.destination_warehouse_id = res.order_id.destination_warehouse_id
            else:
                if not res.destination_warehouse_id:
                    res.destination_warehouse_id = res.order_id.destination_warehouse_id or self.env['stock.warehouse'].search([],limit=1)
            if res.destination_warehouse_id:
                res.picking_type_id = res.destination_warehouse_id.in_type_id.id
    
    # OVEERIDE eq_po_multi_warehouse
    @api.onchange('product_id')
    def onchange_custom_product_id(self):
        pass

    @api.onchange('date_planned')
    def set_date(self):
        for res in self:
            if res.order_id.is_delivery_receipt:
                res.date_planned = res.order_id.date_planned
            else:
                if not res.date_planned:
                    res.date_planned = False


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    purchase_id = fields.Many2one('purchase.order', string="Purchase Order")