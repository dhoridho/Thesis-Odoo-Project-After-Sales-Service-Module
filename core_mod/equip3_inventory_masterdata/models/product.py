import ast, re

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import base64
from odoo import tools
from lxml import etree
from itertools import groupby
from odoo.modules import get_module_resource
import json
import json as simplejson
from xml.dom import minidom

import xml.etree.ElementTree as ET


# class ProductTemplate(models.Model):

#     _inherit="product.template"

#     bundling_price = fields.Float(string='Bundling Cost', compute='_compute_bundling_price', store=True)


class ProductVariantAttributeValue(models.Model):
    _name = 'product.variant.attribute.value'
    _description = "Product Variant Attribute Value"

    template_id = fields.Many2one('product.template', string='Template')
    brand_value_ids = fields.Many2many('product.brand', string='Brand Attribute Values')
    attribute_value_ids = fields.Many2many('product.template.attribute.value',
                'product_variant_attribute_value_rel',
                string='Attribute Values')


class StockProduct(models.Model):
    _inherit = 'product.template'

    brand_attribute_id = fields.Many2one('product.attribute', string="Brand Attribute", compute='compute_brand_attribute_id')
    # unused field
    brand_ids = fields.Many2many('product.brand', string='Unused Brands')

    product_brand_ids = fields.Many2many('product.brand','product_brand_relation', 'tmpl_id', 'brand_id', string='Brands')
    asset_entry_perqty = fields.Boolean('Asset Entry Perquantity')
    company_id_domain = fields.Char(string='Company Domain', compute='compute_company_id_domain')
    product_ratio_line = fields.One2many(comodel_name='product.ratio.line', inverse_name='product_tmpl_id', string='Custom UoM Line')
    uom_categ_id = fields.Many2one(comodel_name='uom.category', string='UoM Category', related='uom_id.category_id')
    company_ids = fields.Many2many(comodel_name='res.company', string='Companies')
    barcode_ean13_value = fields.Char(string='Barcode Value', compute="_compute_ean13_value", store=True)
    barcode_type = fields.Char(string='Barcode Type', compute="_compute_barcode_type")

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Products'),
            'template': '/equip3_inventory_masterdata/static/src/xls/product_template.xlsx'

        }]

    @api.depends('barcode')
    def _compute_ean13_value(self):
        barcode_type = self._get_barcode_type()
        if barcode_type == 'EAN13':
            for record in self:
                record.barcode_ean13_value = False
                if record.barcode and record.barcode.isdigit():
                    record.barcode_ean13_value = self._get_ean13_barcode_value(record.barcode)

    def _compute_barcode_type(self):
        barcode_type = self._get_barcode_type()
        for record in self:
            record.barcode_type = barcode_type

    def _get_barcode_type(self):
        configuration = self.env['barcode.configuration'].search([], limit=1)
        return configuration.barcode_type if configuration else None

    def _get_ean13_barcode_value(self, barcode):
        if not barcode:
            return False

        barcode_length = len(barcode)
        if barcode_length == 12 and barcode.isdigit():
            return barcode + self._calculate_ean13_checksum(barcode)
        elif barcode_length < 12 or barcode_length == 13:
            return barcode
        else:
            return False

    def _calculate_ean13_checksum(self, barcode):
        sum_odd = sum(int(barcode[i]) for i in range(0, 12, 2))
        sum_even = sum(int(barcode[i]) for i in range(1, 12, 2)) * 3
        checksum = (10 - ((sum_odd + sum_even) % 10)) % 10
        # print('➡ sum_odd:', sum_odd, 'sum_even:', sum_even, 'checksum:', checksum)
        return str(checksum)


    @api.depends('company_id')
    def compute_company_id_domain(self):
        for record in self:
            record.company_id_domain = False
            company_ids = self.env['res.company'].search([('id', 'in', self.env.user.company_ids.ids)])
            if company_ids:
                record.company_id_domain = json.dumps([('id', 'in', company_ids.ids)])


    def compute_brand_attribute_id(self):
        brand_id = self.env['product.attribute'].sudo().search([('name','=ilike','Brand')], limit=1)
        for record in self:
            record.brand_attribute_id = brand_id and brand_id.id or False


    @api.onchange('product_brand_ids')
    def variant_attribute_value_move_ids(self):
        if self.product_brand_ids:
            attribute_value_data = []
            attribute_obj = self.env['product.attribute'].search([('name', '=', 'Brand')],limit=1)

            all_value_ids = []
            for rec in self.product_brand_ids:
                value_ids = self.env['product.attribute.value'].search(
                    [('attribute_id', '=', attribute_obj.id), ('name', '=ilike', rec.brand_name)]).ids
                for val in value_ids:
                    if val not in all_value_ids:
                        all_value_ids.append(val)
            # if not all_value_ids:
            #     raise ValidationError('No attribute value for selected brand')

            variant_data= []
            attribute_ids = self.attribute_line_ids.mapped('attribute_id').ids
            if attribute_obj.id not in attribute_ids:
                variant_data.append((0, 0, {
                    'attribute_id': attribute_obj.id,
                    'value_ids': [(6, 0, all_value_ids)],
                }))
            else:
                attribute_line = self.attribute_line_ids.filtered(
                    lambda r: r.attribute_id.id == attribute_obj.id)
                if attribute_line:
                    variant_data.append((1, attribute_line.id, {
                        'value_ids': [(4, value) for value in all_value_ids],
                    }))

            self.attribute_line_ids = variant_data

    @api.model
    def _get_default_image_value(self, type):
        if type == 'asset':
            image_path = get_module_resource('equip3_inventory_masterdata', 'static/src/img', 'asset.png')
        elif type == 'consu':
            image_path = get_module_resource('equip3_inventory_masterdata', 'static/src/img', 'consumable.png')
        elif type == 'service':
            image_path = get_module_resource('equip3_inventory_masterdata', 'static/src/img', 'service.png')
        elif type == 'product':
            image_path = get_module_resource('equip3_inventory_masterdata', 'static/src/img', 'storable.png')
        else:
            image_path = get_module_resource('equip3_inventory_masterdata', 'static/src/img', 'storable.png')
        return base64.b64encode(open(image_path, 'rb').read())

    @api.model
    def create(self, vals):
        if 'type' in vals:
            vals['image_1920'] = self._get_default_image_value(vals['type'])
        return super(StockProduct, self).create(vals)

    create_date = fields.Datetime('Created On', tracking=True, readonly='1')
    create_uid = fields.Many2one('res.users', 'Created by', tracking=True, readonly='1')
    branch_id = fields.Many2one('res.branch', 'Branch', tracking=True)
    # multi_companies_all = fields.Many2many('res.company', 'product_id', 'company_id', 'prod_comp_id', string='Allowed  Companies', tracking=True)
    secondary_uom_id = fields.Many2one(
        'uom.uom', 'Secondary UoM',
        help="Default unit of measure used for all stock operations.", tracking=True)
    multi_warehouses_all = fields.Many2many('stock.warehouse', 'prod_id', 'warehouse_id', 'prod_warehouse_id',  string='Allowed Multi Warehouses', tracking=True)

    is_sn_autogenerate = fields.Boolean(string="Serial Number Auto Generated By System")
    is_use_product_code = fields.Boolean(string="Use Product Code For Serial Number")
    sn_prefix = fields.Char(string="Serial Number Prefix")
    suffix = fields.Char(string="Serial Number Suffix")
    digits = fields.Integer(string="Digits", default=3)
    current_sequence = fields.Char(string="Current Sequence", default='1')
    is_product_service_operation = fields.Boolean(string="Product Service Operation")
    is_product_service_operation_receiving = fields.Boolean(string="Product Service Operation Receiving")
    is_product_service_operation_delivery = fields.Boolean(string="Product Service Operation Delivery")
    is_in_autogenerate = fields.Boolean(string="Lot Number Auto Generated By System")
    is_in_use_product_code = fields.Boolean(string="Use Product Code For Lot Number")
    in_prefix = fields.Char(string="Lot Number Prefix")
    in_suffix = fields.Char(string="Lot Number Suffix")
    in_digits = fields.Integer(string="Lot Digits", default=3)
    in_current_sequence = fields.Char(string="Lot Current Sequence", default=1)
    multi_barcode = fields.Boolean('Multi Barcode')
    is_variants = fields.Boolean('is_variants', compute='check_variant', default=False)
    barcode_line_vals = fields.Char()
    barcode_dup = fields.Char()
    selected_barcode_in_pl_report = fields.Char()
    barcode_labels_line_data = fields.Text()
    def_packaging_id = fields.Many2one('product.packaging', string="Default Packaging", compute='_compute_package_id', inverse='_inverse_package_id', store=True)
    group_stock_ids = fields.Many2many('product.packaging', compute="_compute_is_group_stock", string='Group Stock')
    reordering_rules_ids = fields.One2many('stock.warehouse.orderpoint', 'product_id', compute="_compute_reordering_rules", string='Reordering Rules')
    nbr_reordering_rules = fields.Integer(string='Reordering Rules Count')
    length = fields.Float(string="Length", copy=False)
    width = fields.Float(string="Width", copy=False)
    height = fields.Float(string="Height", copy=False)
    variant_attribute_value_ids = fields.One2many('product.variant.attribute.value',
                                        'template_id', string="Product Template Attribute Value")
    volume_calculation = fields.Boolean(string="Volume Calculation")
    volume_formula = fields.Char(string="Volume Calculation Formula")
    hide = fields.Boolean('hide', compute='check_ids', default=False)

    expiration_time = fields.Integer(string="Expiration Time", help="Counted based on product arrival within the warehouse, added with the designated days")
    use_time = fields.Integer(string="Best Before Time", help="Counted based on date of expiration time, added with the designated days")
    removal_time = fields.Integer(string="Removal Time", help="Counted based on date of expiration time, added with the designated days, the product will be removal from stock")
    alert_time = fields.Integer(string="Alert Time", help="Counted based on product arrival within the warehouse, added with the designated days")

    categ_id = fields.Many2one('product.category', default=False)
    brand_setting = fields.Selection(related="company_id.brand_setting")
    domain_uom_id = fields.Char('Uom Domain', compute='_compute_domain_uom_id')
    product_limit = fields.Selection([('no_limit',"Don't Limit"),('limit_per','Limit by Precentage %'),('limit_amount','Limit by Amount'),('str_rule','Strictly Limit by Purchase Order')],
		string='Receiving Limit', tracking=True, default=False)
    min_val = fields.Integer('Minimum Value')
    max_val = fields.Integer('Maximum Value')
    delivery_limit = fields.Selection([('no_limit',"Don't Limit"),('limit_per','Limit by Precentage %'),('limit_amount','Limit by Amount'),('str_rule','Strictly Limit by Sale Order')],
		string='Delivery Limit', tracking=True, default=False)
    delivery_limit_min_val = fields.Integer('Minimum Value')
    delivery_limit_max_val = fields.Integer('Maximum Value')

    @api.depends('uom_id')
    def _compute_domain_uom_id(self):
        if self.uom_id:
            category_id = self.uom_id.category_id.id if self.uom_id.category_id else False
            if category_id:
                self.domain_uom_id = json.dumps([('category_id', '=', category_id)])
            else:
                self.domain_uom_id = json.dumps([('id', 'in', [])])
        else:
            self.domain_uom_id = json.dumps([('id', 'in', [])])


    def compute_all_image(self):
        product_template = self.env['product.template'].search([])
        for rec in product_template:
            if rec.type:
                # category_name = self.env['product.category'].search([('id', '=', rec.categ_id.id)])
                if rec.type == 'asset':
                    image_path = get_module_resource('equip3_inventory_masterdata', 'static/src/img', 'asset.png')
                    rec.image_1920 = base64.b64encode(open(image_path, 'rb').read())

                elif rec.type == 'consu':
                    image_path = get_module_resource('equip3_inventory_masterdata', 'static/src/img', 'consumable.png')
                    rec.image_1920 = base64.b64encode(open(image_path, 'rb').read())

                elif rec.type == 'service':
                    image_path = get_module_resource('equip3_inventory_masterdata', 'static/src/img', 'service.png')
                    rec.image_1920 = base64.b64encode(open(image_path, 'rb').read())

                elif rec.type == 'product':
                    image_path = get_module_resource('equip3_inventory_masterdata', 'static/src/img', 'storable.png')
                    rec.image_1920 = base64.b64encode(open(image_path, 'rb').read())

    @api.onchange('type')
    def _onchange_type_change_categ(self):
        if self.type == 'consu':
            product_category = self.env['product.category'].search([('stock_type', '=', 'consu'),('name','=','Consumable')], limit=1)
            self.categ_id = product_category.id
            image_path = get_module_resource('equip3_inventory_masterdata', 'static/src/img', 'consumable.png')
            self.image_1920 = base64.b64encode(open(image_path, 'rb').read())
        elif self.type == 'service':
            product_category = self.env['product.category'].search([('stock_type', '=', 'service'),('name','=','Service')], limit=1)
            self.categ_id = product_category.id
            image_path = get_module_resource('equip3_inventory_masterdata', 'static/src/img', 'service.png')
            self.image_1920 = base64.b64encode(open(image_path, 'rb').read())
        elif self.type == 'product':
            product_category = self.env['product.category'].search([('stock_type', '=', 'product'),('name','=','Storable Product')], limit=1)
            self.categ_id = product_category.id
            image_path = get_module_resource('equip3_inventory_masterdata', 'static/src/img', 'storable.png')
            self.image_1920 = base64.b64encode(open(image_path, 'rb').read())
        elif self.type == 'asset':
            self.tracking = 'none'
            product_category = self.env['product.category'].search([('stock_type', '=', 'asset'),('name','=','Asset')], limit=1)
            self.categ_id = product_category.id
            image_path = get_module_resource('equip3_inventory_masterdata', 'static/src/img', 'asset.png')
            self.image_1920 = base64.b64encode(open(image_path, 'rb').read())
        else:
            pass

    @api.model
    def default_get(self, fields):
        res = super(StockProduct, self).default_get(fields)
        product_type = res.get('type')
        if product_type and 'categ_id' not in res:
            categ = self.env['product.category'].search([('stock_type', '=', product_type)], limit=1)
            res.update({'categ_id': categ.id})

        barcode_type = self._get_barcode_type()
        res.update({'barcode_type': barcode_type if barcode_type else ''})
        return res

    @api.depends('variant_attribute_value_ids')
    def check_ids(self):
        self.hide = False
        for x in self:
            record = self.env['product.product'].search([ ('product_tmpl_id' , '=', x.id)])
            not_active = self.env['product.product'].search([('product_tmpl_id' , '=', x.id),('active' , '=', False)])

            if len(self.variant_attribute_value_ids) >= 1:
                self.hide = True

            if len(record) >= 2:
                self.hide = True

            if len(not_active) > 1:
                self.hide = True

    @api.onchange('volume_calculation', 'volume_formula', 'height', 'width', 'length')
    def _calculate_expression(self):
        for record in self:
            formula = ''
            if record.volume_formula:
                formula = record.volume_formula
                formula = formula.replace("height", str(record.height))
                formula = formula.replace("width", str(record.width))
                formula = formula.replace("length", str(record.length))
            try:
                record.volume = eval(formula)
            except Exception:
                record.volume = 0

    def _onchange_attribute_ids(self):
        for record in self:
            record.variant_attribute_value_ids.unlink()
            data = []
            for variant in record.product_variant_ids:
                data.append((0, 0, {
                    'attribute_value_ids': [(6, 0, variant.product_template_attribute_value_ids.ids)]
                }))
            record.variant_attribute_value_ids = data

    def write(self, vals):
        variant_attribute_data = []
        if 'variant_attribute_value_ids' in vals and vals.get('variant_attribute_value_ids'):
            for record in self:
                for line in vals.get('variant_attribute_value_ids'):
                    if line[0] == 2:
                        variant_line = record.variant_attribute_value_ids.filtered(lambda r:r.id == line[1])
                        variant_attribute_data.append({'attribute_value': variant_line.attribute_value_ids.ids})
        res = super(StockProduct, self).write(vals)
        if 'attribute_line_ids' in vals and vals.get('attribute_line_ids'):
            for record in self:
                record._onchange_attribute_ids()
        if len(variant_attribute_data) > 0:
            for record in self:
                for variant_attribute_line in variant_attribute_data:
                    variant_id = record.product_variant_ids.filtered(lambda r: r.product_template_attribute_value_ids.ids == variant_attribute_line.get('attribute_value'))
                    if not variant_id:
                        continue
                    variant_id.write({'active': False})

        barcode_type = self._get_barcode_type()
        if barcode_type == 'EAN13':
            if vals.get('barcode') and vals['barcode'].isdigit():
                if len(vals['barcode']) <= 12:
                    barcode_value = vals['barcode'].zfill(12)
                else:
                    barcode_value = vals['barcode']
                super(StockProduct, self).write({'barcode': barcode_value})
        return res

    @api.depends('packaging_ids')
    def _compute_package_id(self):
        for record in self:
            record.def_packaging_id = False
            packaging_ids = self.env['product.packaging'].search([('product_id', 'in', record.product_variant_ids.ids)])
            if packaging_ids:
                record.def_packaging_id = packaging_ids[0].id

    def _compute_reordering_rules(self):
        for record in self:
            rules = reordering_rules_rec = self.env['stock.warehouse.orderpoint'].search([('product_id', 'in', record.product_variant_ids.ids)])
            record.reordering_rules_ids = [(6, 0 , rules.ids)]

    def _inverse_package_id(self):
        pass

    def _compute_is_group_stock(self):
        for rec in self:
            packaging_ids = self.env['product.packaging'].search([('product_id', 'in', rec.product_variant_ids.ids)])
            rec.group_stock_ids = [(6, 0, packaging_ids.ids)]

    @api.depends('product_variant_ids', 'product_variant_ids.packaging_ids')
    def _compute_packaging_ids(self):
        for p in self:
            if len(p.product_variant_ids) == 1:
                packaging_ids = self.env['product.packaging'].search([('product_id', 'in', p.product_variant_ids.ids)])
                p.packaging_ids = packaging_ids
            else:
                p.packaging_ids = False

    def _set_packaging_ids(self):
        for p in self:
            if len(p.product_variant_ids) == 1:
                p.product_variant_ids.packaging_ids = [(6, 0, p.packaging_ids)]

    @api.onchange('multi_barcode')
    def barcode_value(self):
        for record in self:
            if not record.multi_barcode:
                record.barcode = record.barcode_dup
            for product in self.product_variant_ids:
                product.barcode_line_ids = self.barcode_line_ids.ids

    @api.onchange('barcode')
    def compute_barcode_dup(self):
        barcode_type = self._get_barcode_type()
        for record in self:
            record.sh_qr_code = record.barcode
            if barcode_type == 'EAN13':
                if record.barcode and isinstance(record.barcode, str):
                    if not record.barcode.isdigit() or len(record.barcode) != 13:
                        raise ValidationError("Select valid barcode type according to barcode field value or check value in the field!")
            record.barcode_dup = record.barcode

    @api.constrains('in_prefix', 'sn_prefix')
    def _check_prefix_limit(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        prefix_limit = int(IrConfigParam.get_param('prefix_limit', 5))
        for record in self:
            if record.tracking == 'lot' and record.in_prefix and record.is_in_autogenerate and len(record.in_prefix) > prefix_limit:
                raise ValidationError("Prefix value size must be less or equal to %s" % (prefix_limit))
            if record.tracking == 'serial' and record.sn_prefix and record.is_sn_autogenerate and len(record.sn_prefix) > prefix_limit:
                raise ValidationError("Prefix value size must be less or equal to %s" % (prefix_limit))


    # @api.onchange('multi_barcode')
    # def get_barcode_value(self):
    #    for record in self:
    #        if record.multi_barcode:


    def check_variant(self):
        if self.attribute_line_ids:
            self.is_variants = True
        else:
            self.is_variants = False
        if self.barcode_line_ids:
            self.barcode_line_vals = ''
            for name in self.barcode_line_ids:
                self.barcode_line_vals += name.name
        for product in self.product_variant_ids:
            product.barcode_line_vals = self.barcode_line_vals
            if self.multi_barcode:
                product.multi_barcode = True
            else:
                product.multi_barcode = False

    @api.onchange('tracking', 'name')
    def _onchange_product_tracking(self):
        self.sn_prefix = False
        self.in_prefix = False
        if self.tracking == 'lot':
            if self.name:
                split_name = self.name.split(" ")
                if len(split_name) == 1:
                    name = split_name[0][:3].upper()
                    self.in_prefix = name
                elif len(split_name) == 2:
                    name = split_name[0][0]
                    name_1 = split_name[1][0]
                    name_2 = ''
                    if len(split_name[1]) > 1:
                        name_2 = split_name[1][1]
                    final_name = (name + name_1 + name_2).upper()
                    self.in_prefix = final_name
                elif len(split_name) > 2:
                    name = split_name[0][0]
                    name_1 = split_name[1][0]
                    name_2 = split_name[2][0]
                    final_name = (name + name_1 + name_2).upper()
                    self.in_prefix = final_name
            self.is_in_autogenerate = True
            self.is_use_product_code = False
        elif self.tracking == 'serial':
            if self.name:
                split_name = self.name.split(" ")
                if len(split_name) == 1:
                    name = split_name[0][:3].upper()
                    self.sn_prefix = name
                elif len(split_name) == 2:
                    name = split_name[0][0]
                    name_1 = split_name[1][0]
                    name_2 = ''
                    if len(split_name[1]) > 1:
                        name_2 = split_name[1][1]
                    final_name = (name + name_1 + name_2).upper()
                    self.sn_prefix = final_name
                elif len(split_name) > 2:
                    name = split_name[0][0]
                    name_1 = split_name[1][0]
                    name_2 = split_name[2][0]
                    final_name = (name + name_1 + name_2).upper()
                    self.sn_prefix = final_name
            self.is_sn_autogenerate = True
            self.is_in_use_product_code = False
        else:
            self.is_in_autogenerate = False
            self.is_in_use_product_code = False
            self.is_sn_autogenerate = False
            self.is_use_product_code = False

    @api.constrains('is_in_use_product_code', 'in_prefix')
    def _check_value_lot(self):
        for record in self:
            if record.is_in_autogenerate and not record.is_in_use_product_code and record.in_prefix:
                check_value = self.search([('is_in_use_product_code', '=', False), ('in_prefix', '=', record.in_prefix), ('id', '!=', record.id)], limit=1)
                if check_value:
                    raise ValidationError(_('Lot Number Prefix Must Be Unique'))

    @api.constrains('is_use_product_code', 'sn_prefix')
    def _check_value(self):
        for record in self:
            if record.is_sn_autogenerate and not record.is_use_product_code and record.sn_prefix:
                check_value = self.search([('is_use_product_code', '=', False), ('sn_prefix', '=', record.sn_prefix), ('id', '!=', record.id)], limit=1)
                if check_value:
                    raise ValidationError(_('Serial Number Prefix Must Be Unique'))

    @api.onchange('digits')
    def _onchange_digits(self):
        number = self.current_sequence.lstrip('0')
        if self.digits < len(number):
            raise ValidationError(_('Digits Not Acceptable!'))
        current_sequence_length = len(self.current_sequence)
        if self.digits > current_sequence_length:
            number_length = len(number)
            original_number_length = self.digits - number_length
            add_zero_original_number = '0' * original_number_length
            self.current_sequence = add_zero_original_number + number
        elif self.digits < current_sequence_length:
            self.current_sequence = self.current_sequence[-self.digits:]

    @api.onchange('in_digits')
    def _onchange_in_digits(self):
        number = self.in_current_sequence.lstrip('0')
        if self.in_digits < len(number):
            raise ValidationError(_('Digits Not Acceptable!'))
        in_current_sequence_length = len(self.in_current_sequence)
        if self.in_digits > in_current_sequence_length:
            number_length = len(number)
            original_number_length = self.in_digits - number_length
            add_zero_original_number = '0' * original_number_length
            self.in_current_sequence = add_zero_original_number + number
        elif self.in_digits < in_current_sequence_length:
            self.in_current_sequence = self.in_current_sequence[-self.in_digits:]

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        user = self.env.user
        domain = domain or []
        domain.extend(['|',('multi_companies_all', '=', False),('multi_companies_all', 'in', user.company_ids.ids)])
        return super(StockProduct, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        user = self.env.user
        domain = domain or []
        domain.extend(['|',('multi_companies_all', '=', False),('multi_companies_all', 'in', user.company_ids.ids)])
        return super(StockProduct, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit,
                                                                orderby=orderby, lazy=lazy)

    def _get_next_lot_and_serial(self, current_sequence=False, join=True, start_from=1):
        self.ensure_one()
        if self.tracking not in ('lot', 'serial'):
            return False

        if self.tracking == 'serial':
            is_auto_generate = self.is_sn_autogenerate
            is_use_product_code = self.is_use_product_code
            prefix = self.sn_prefix
            suffix = self.suffix
            digits = self.digits
        else:
            is_auto_generate = self.is_in_autogenerate
            is_use_product_code = self.is_in_use_product_code
            prefix = self.in_prefix
            suffix = self.in_suffix
            digits = self.in_digits

        if not is_auto_generate:
            return False

        default_code = is_use_product_code and self.default_code or False

        number = start_from
        while True:
            current_sequence = str(number).zfill(digits)
            sequence = [default_code, prefix, current_sequence, suffix]
            lot_name = ''.join([seq for seq in sequence if seq])
            if not self.env['stock.production.lot'].search([
                ('name', '=', lot_name),
                ('product_id', '=', self.product_variant_id.id)
            ], limit=1):
                break
            number += 1

        if not join:
            return sequence
        return ''.join([seq for seq in sequence if seq])

    def action_create_variants(self):
        context = dict(self.env.context) or {}
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Variants',
            'view_mode': 'form',
            'res_model': 'product.template.create.variant',
            'domain' : [],
            'context': context,
            'target': 'new'
        }

    def action_delete_variants(self):
        for record in self:
            template_id = record.variant_attribute_value_ids.mapped('template_id')
            product_variant_ids = template_id.mapped('product_variant_ids')
            product_variant_ids.write({'active': False})
            record.variant_attribute_value_ids.unlink()
            record.attribute_line_ids.unlink()

    @api.constrains('min_val', 'max_val', 'product_limit')
    def _onchange_value(self):
        if self.product_limit == 'limit_per' and self.min_val > 0 and self.max_val > 0 and self.min_val > self.max_val:
            raise ValidationError(_("Minimum value can't be more than maximum value"))
        
    @api.constrains('min_val_delivery_limit', 'max_val_delivery_limit', 'delivery_limit')
    def _onchange_value(self):
        if self.delivery_limit == 'limit_per' and self.min_val_delivery_limit > 0 and self.max_val_delivery_limit > 0 and self.min_val_delivery_limit > self.max_val_delivery_limit:
            raise ValidationError(_("Minimum value can't be more than maximum value"))

    @api.constrains('current_sequence', 'in_current_sequence', 'digits', 'in_digits')
    def _check_sequence(self):
        for record in self.filtered(lambda o: o._is_auto()):
            if record._is_lot_auto():
                sequence = 'in_current_sequence'
                digits = 'in_digits'
            else:
                sequence = 'current_sequence'
                digits = 'digits'

            if len(record[sequence]) != record[digits]:
                raise ValidationError(_("Current sequence doesn't match digits!"))

            if not record[sequence].isdigit():
                raise ValidationError(_('Current sequence anly allow digits!'))

    def _is_lot_auto(self):
        self.ensure_one()
        return self.tracking == 'lot' and self.is_in_autogenerate

    def _is_sn_auto(self):
        self.ensure_one()
        return self.tracking == 'serial' and self.is_sn_autogenerate

    def _is_auto(self):
        return self._is_lot_auto() or self._is_sn_auto()

    def _update_current_sequence(self, moves):
        self.ensure_one()
        if not self._is_auto():
            return

        sequence = self._get_next_lot_and_serial(join=False)
        sequence[-2] = '(\\d+)'
        lot_exp = ''.join([seq for seq in sequence if seq])

        lot_numbers = []
        for move_line in moves.mapped('move_line_ids'):
            lot_name = move_line.lot_id.name or move_line.lot_name or ''
            exp_match = re.search(lot_exp, lot_name)
            if exp_match:
                lot_numbers += [int(exp_match.group(1))]

        if not lot_numbers:
            return

        max_lot_numbers = max(lot_numbers)
        next_current_sequence = max_lot_numbers + 1

        if self.tracking == 'serial':
            digits = self.digits
            sequence_field = 'current_sequence'
        else:
            digits = self.in_digits
            sequence_field = 'in_current_sequence'

        self[sequence_field] = str(next_current_sequence).zfill(digits)


class StockProductInherit(models.Model):
    _inherit = 'product.product'

    variant_short_name = fields.Char('Short Name', compute='_compute_variant_short_name')
    multi_barcode = fields.Boolean('Multi Barcode')
    is_variants = fields.Boolean('is_variants', compute='check_variant', default=False)
    barcode_line_vals = fields.Char()
    barcode_dup = fields.Char()
    packaging_ids = fields.Many2many(
        'product.packaging', string='Product Packages',
        help="Gives the different ways to package the same product.")
    volume_calculation = fields.Boolean(string="Volume Calculation")
    volume_formula = fields.Char(string="Volume Calculation Formula")

    def _get_next_lot_and_serial(self, current_sequence=False, join=True):
        return self.product_tmpl_id._get_next_lot_and_serial(current_sequence=current_sequence, join=join)

    def _is_lot_auto(self):
        return self.product_tmpl_id._is_lot_auto()

    def _is_sn_auto(self):
        return self.product_tmpl_id._is_sn_auto()

    def _is_auto(self):
        return self.product_tmpl_id._is_auto()

    def _update_current_sequence(self, moves):
        return self.product_tmpl_id._update_current_sequence(moves)

    @api.onchange('type')
    def _onchange_type_change_categ(self):
        if self.type == 'consu':
            image_path = get_module_resource('equip3_inventory_masterdata', 'static/src/img', 'consumable.png')
            self.image_1920 = base64.b64encode(open(image_path, 'rb').read())
        elif self.type == 'service':
            image_path = get_module_resource('equip3_inventory_masterdata', 'static/src/img', 'service.png')
            self.image_1920 = base64.b64encode(open(image_path, 'rb').read())
        elif self.type == 'product':
            image_path = get_module_resource('equip3_inventory_masterdata', 'static/src/img', 'storable.png')
            self.image_1920 = base64.b64encode(open(image_path, 'rb').read())
        elif self.type == 'asset':
            image_path = get_module_resource('equip3_inventory_masterdata', 'static/src/img', 'asset.png')
            self.image_1920 = base64.b64encode(open(image_path, 'rb').read())
        else:
            pass

    @api.onchange('multi_barcode')
    def barcode_value(self):
        for record in self:
            if record.multi_barcode == False:
                record.barcode = record.barcode_dup

    @api.onchange('volume_calculation', 'volume_formula', 'height', 'width', 'length')
    def _calculate_expression(self):
        for record in self:
            formula = ''
            if record.volume_formula:
                formula = record.volume_formula
                formula = formula.replace("height", str(record.height))
                formula = formula.replace("width", str(record.width))
                formula = formula.replace("length", str(record.length))
            try:
                record.volume = eval(formula)
            except Exception:
                record.volume = 0

    def get_barcode_details(self):
        data = ast.literal_eval(self.product_tmpl_id.barcode_labels_line_data)
        index = [x for x, y in enumerate(data) if y[0] == self.id][0]
        product_tmpl_ids = self.env["product.product"].browse(list(set(i[0] for i in data))).mapped("product_tmpl_id")
        current_pro_barcode = data.pop(index)[1]
        new_dict = [(i[0],i[1]) for i in data]
        for product in product_tmpl_ids:
            product.barcode_labels_line_data = new_dict
        return current_pro_barcode

    @api.onchange('barcode')
    def compute_barcode_dup(self):
        for record in self:
            record.barcode_dup = record.barcode

    def check_variant(self):
        if self.attribute_line_ids:
            self.is_variants = True
        else:
            self.is_variants = False
        if self.barcode_line_ids:
            str = ''
            for name in self.barcode_line_ids:
                str += name.name
            # str += ''
            new_str=''
            # for i in range(len(str)):
            #     if i != 1:
            #         new_str = new_str + str[i]
            self.barcode_line_vals = str

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        user = self.env.user
        domain = domain or []
        domain.extend(['|',('multi_companies_all', '=', False),('multi_companies_all', 'in', user.company_ids.ids)])
        return super(StockProductInherit, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        user = self.env.user
        domain = domain or []
        domain.extend(['|',('multi_companies_all', '=', False),('multi_companies_all', 'in', user.company_ids.ids)])
        return super(StockProductInherit, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit,
                                                                orderby=orderby, lazy=lazy)

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if not args:
            args = []
        user = self.env.user
        args.extend(['|',('multi_companies_all', '=', False),('multi_companies_all', 'in', user.company_ids.ids)])
        return super(StockProductInherit, self)._name_search(name=name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)

    def _compute_variant_short_name(self):
        for record in self:
            if record.product_template_attribute_value_ids:
                name_string = ''
                for att_values in record.product_template_attribute_value_ids:
                    # print('name',name)
                    # print('na00me',name.name)
                    # print('att_name',att_values.attribute_id.name)
                    for att in att_values.attribute_id.value_ids:
                        if att.name == att_values.name:

                            # print('attsn',att.short_name)
                    # for values in name:
                    #     print('vals',values.short_name)
                            string = str(att.short_name)
                    # print('string',string[:2])
                            if att.short_name:
                                name_string = name_string + string
                if name_string:
                    record.variant_short_name = str(name_string)
                else:
                    record.variant_short_name = False
            else:
                record.variant_short_name = False
