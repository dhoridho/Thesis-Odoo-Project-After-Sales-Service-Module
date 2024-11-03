# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models, _
from odoo.exceptions import UserError
import datetime


class SaleAdvWizard(models.TransientModel):
    _name = "sale.adv.wizard"
    _description = "Sale Multi Product Selection Advanced Wizard"

    product_ids = fields.One2many(
        "sale.adv.wizard.product.line",
        "sale_adv_wizard_id",
        string="Products"
    )
    product_attr_ids = fields.Many2many(
        "product.attribute.value",
        string="Attributes"
    )
    specific_product_ids = fields.One2many(
        "sale.adv.wizard.product.line.specific",
        "sale_adv_wizard_id_specific",
        string="Specific Products"
    )
    order_id = fields.Integer("Order ID")

    def sh_sale_adv_select_btn(self):
        if(
                self and
                self.product_ids and
                self.order_id
        ):
            for data in self:
                order_id = data.order_id
                sale_order_line_obj = self.env['sale.order.line']
                for rec in data.product_ids:
                    if rec.uom_po_id:
                        created_pol = sale_order_line_obj.create({
                            'product_id': rec.product_id.id,
                            'name': rec.product_id.name,
                            'order_id': order_id,
                            'product_uom_qty': rec.qty,
                            'multiple_do_date': datetime.datetime.now(),
                            'price_unit': rec.product_id.lst_price,
                            'product_uom': rec.uom_po_id.id,
                        })

    def sh_sale_adv_select_specific_btn(self):
        if(
                self and
                self.specific_product_ids and
                self.order_id
        ):
            for data in self:
                order_id = data.order_id
                sale_order_line_obj = self.env['sale.order.line']
                for rec in data.specific_product_ids:
                    if rec.uom_po_id:
                        created_pol = sale_order_line_obj.create({
                            'product_id': rec.product_id.id,
                            'name': rec.product_id.name,
                            'order_id': order_id,
                            'product_uom_qty': rec.qty,
                            'multiple_do_date': datetime.datetime.now(),
                            'price_unit': rec.product_id.lst_price,
                            'product_uom': rec.uom_po_id.id,
                        })

    def reset_filter(self):
        if self:
            for rec in self:
                rec_dic = rec.read()[0]
                if rec_dic:
                    reset_vals = {}
                    for k, v in rec_dic.items():
                        if "x_" in k and v:
                            reset_vals.update({k: False})
                    reset_vals.update({'product_attr_ids': None})
                    rec.product_attr_ids = None
                    rec.write(reset_vals)

                    return {
                        'name': 'Select Products Advance',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'sale.adv.wizard',
                        'view_id': False,
                        'type': 'ir.actions.act_window',
                        'res_id': rec.id,
                        'target': 'new',
                    }

    def reset_list(self):
        if self:
            for rec in self:
                rec.product_ids = None
                return {
                    'name': 'Select Products Advance',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sale.adv.wizard',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'res_id': rec.id,
                    'target': 'new',
                }

    def reset_specific(self):
        if self:
            for rec in self:
                rec.specific_product_ids = None
                return {
                    'name': 'Select Products Advance',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sale.adv.wizard',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'res_id': rec.id,
                    'target': 'new',
                }

    def filter_products(self):
        if self:
            for rec in self:
                rec.order_id = self.env.context.get('active_id', False)
                rec_dic = rec.read()[0]
                domain = []
                if rec_dic:
                    for k, v in rec_dic.items():
                        if "x_" in k and "x_opt_" not in k:
                            if v:
                                pro_field_name = k.split("_", 1)[1]
                                sale_field_name = "x_opt_" + pro_field_name
                                if rec_dic.get(sale_field_name, False):
                                    opt = rec_dic.get(sale_field_name, False)
                                    domain.append((pro_field_name, opt, v))
                                else:
                                    # if attribute fields found
                                    if "x_attr_" in k:
                                        domain.append((
                                            'product_template_attribute_value_ids', 'in', v[0]
                                        ))
                                    # if boolean fields found
                                    else:
                                        # check whether it's a selection or boolean fields or not
                                        sale_model_id = self.env[
                                            'ir.model'
                                        ].sudo().search([
                                            ('model', '=', 'sale.adv.wizard')
                                        ], limit = 1)
                                        if sale_model_id:
                                            search_field = self.env[
                                                'ir.model.fields'
                                            ].sudo().search([
                                                ('name', '=', ''+ k),
                                                ('model_id', '=', sale_model_id.id),
                                            ], limit = 1)
                                            if search_field:
                                                if search_field.ttype in ['selection','boolean']:
                                                    domain.append((
                                                        pro_field_name, '=', v
                                                    ))
                                                else:
                                                    domain.append((
                                                        pro_field_name, '=', v[0]
                                                    ))
                                            else:
                                                raise UserError(
                                                    _('Field not Found - ' + k)
                                                )

                                        else:
                                            raise UserError(
                                                _('Model not Found - sale.adv.wizard')
                                            )

                        if "product_attr_ids" in k and v:
                            for attr_id in v:
                                domain.append((
                                    'product_template_attribute_value_ids', 'in', attr_id
                                ))

                    if domain:
                        domain.append(('sale_ok', '=', True))
                        search_products = self.env[
                            'product.product'
                        ].search(domain)
                        if search_products:
                            result = []
                            sale_adv_wizard_product_line_obj = self.env['sale.adv.wizard.product.line']
                            for product in search_products:
                                line_vals = {
                                    'product_id': product.id,
                                }
                                created_line = sale_adv_wizard_product_line_obj.create(line_vals)
                                if created_line:
                                    result.append(created_line.id)

                            rec.product_ids = None
                            rec.product_ids = [(6, 0, result)]
                        else:
                            rec.product_ids = None

                    return {
                        'name': 'Select Products Advance',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'sale.adv.wizard',
                        'view_id': False,
                        'type': 'ir.actions.act_window',
                        'res_id': rec.id,
                        'target': 'new',
                    }



class saleAdvWizardProductLine(models.TransientModel):
    _name = 'sale.adv.wizard.product.line'
    _description = "Sale Multi Product Selection Advanced Wizard Product Line"

    sale_adv_wizard_id = fields.Many2one(
        'sale.adv.wizard',
        string='Searched Product'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product'
    )
    default_code = fields.Char(
        related="product_id.default_code",
        string='Internal Reference'
    )
    standard_price = fields.Float(
        related="product_id.standard_price",
        string="Cost"
    )
    uom_po_id = fields.Many2one(
        "uom.uom",
        related="product_id.uom_po_id",
        string="Unit of Measure"
    )
    qty = fields.Float(string="Qty", default=1.0)

    def add_to_specific(self):
        if self and self.product_id:
            for rec in self:
                sale_adv_wizard_product_line_specific_obj = self.env['sale.adv.wizard.product.line.specific']
                line_vals = {
                    'product_id': rec.product_id.id,
                    'qty': rec.qty,
                    'sale_adv_wizard_id_specific': rec.sale_adv_wizard_id.id
                }
                sale_adv_wizard_product_line_specific_obj.create(line_vals)
                res_id = rec.sale_adv_wizard_id.id
                rec.unlink()
                return {
                    'name': 'Select Products Advance',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sale.adv.wizard',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'res_id': res_id,
                    'target': 'new',
                }

class saleAdvWizardProductLineSpecific(models.TransientModel):
    _name = 'sale.adv.wizard.product.line.specific'
    _description = "Sale Multi Pro Selection Adv Wizard Pro Line Specific"

    sale_adv_wizard_id_specific = fields.Many2one(
        'sale.adv.wizard', string='Searched Product')
    product_id = fields.Many2one(
        'product.product',
        string='Product'
    )
    default_code = fields.Char(
        related="product_id.default_code",
        string='Internal Reference'
    )
    standard_price = fields.Float(
        related="product_id.standard_price",
        string="Cost"
    )
    uom_po_id = fields.Many2one(
        "uom.uom",
        related="product_id.uom_po_id",
        string="Unit of Measure"
    )
    qty = fields.Float(string="Qty", default=1.0)
