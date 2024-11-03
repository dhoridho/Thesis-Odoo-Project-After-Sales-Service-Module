# -*- coding: utf-8 -*
from odoo import api, fields, models, _
from datetime import datetime, date
from odoo.exceptions import UserError
from lxml import etree

class ProductTemplateBarcode(models.Model):
    _inherit = 'product.template.barcode'

    active = fields.Boolean('Active', default=True)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_combo_product = fields.Boolean(string="Combo Product")
    combo_option_id = fields.Many2one('combo.option', string="Combo Option")
    combo_option_items = fields.One2many('combo.option.item', related="combo_option_id.item_ids", string="Combo Option Items", readonly=True)
    pos_combo_item_ids = fields.One2many('pos.combo.item', 'product_combo_id', string='Combo Items')
    is_combo = fields.Boolean(
        'Combo Bundle/Pack',
        help='Active it and see to tab Combo/Pack and adding Items for Combo Future'
    )
    is_combo_item = fields.Boolean(
        'Dynamic Combo Item',
        help='Allow this product become item combo of Another Product'
    )
    combo_limit = fields.Integer(
        'Combo Item Limit',
        help='Limit combo items can allow cashier add / combo')
    multi_category = fields.Boolean('Multi Category')
    pos_categ_ids = fields.Many2many(
        'pos.category',
        string='POS Multi Category')
    multi_uom = fields.Boolean('Multi Unit')
    price_uom_ids = fields.One2many(
        'product.uom.price',
        'product_tmpl_id',
        string='Price by Sale Unit')
    multi_variant = fields.Boolean('Multi Variant and Attribute')
    cross_selling = fields.Boolean('Cross Selling')
    cross_ids = fields.One2many(
        'product.cross',
        'product_tmpl_id',
        string='Cross Selling Items')
    supplier_barcode = fields.Char(
        'Supplier Barcode', copy=False,
        help="Supplier Barcode Product, You can Input here and scan on POS")
    pos_sequence = fields.Integer('POS Sequence')
    is_voucher = fields.Boolean('Is Voucher/Coupon', default=0)
    # sale_with_package = fields.Boolean('Sale with Package')
    pizza_modifier = fields.Boolean('Pizza Modifier')
    price_unit_each_qty = fields.Boolean('Active Sale Price each Quantity')
    product_price_quantity_ids = fields.One2many(
        'product.price.quantity',
        'product_tmpl_id',
        'Price each Quantity')
    qty_warning_out_stock = fields.Float('Qty Warning out of Stock', default=10)
    combo_price = fields.Float(
        'Combo Item Price',
        help='This Price will replace public price and include to Line in Cart'
    )
    combo_limit_ids = fields.One2many(
        'pos.combo.limit',
        'product_tmpl_id',
        'Combo Limited Items by Category'
    )
    name_second = fields.Char(
        'Second Name',
        help='If you need print pos receipt Arabic,Chinese...language\n'
             'Input your language here, and go to pos active Second Language')
    special_name = fields.Char('Special Name')
    uom_ids = fields.Many2many('uom.uom', string='Units the same category', compute='_get_uoms_the_same_category')
    note_ids = fields.Many2many(
        'pos.note',
        'product_template_note_rel',
        'product_tmpl_id',
        'note_id',
        string='Notes Fixed'
    )
    tag_ids = fields.Many2many(
        'pos.tag',
        'product_template_tag_rel',
        'product_tmpl_id',
        'tag_id',
        string='Tags'
    )
    pos_branch_id = fields.Many2one(
        'res.branch',
        string = "Branch",
        default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, 
        domain=lambda self: [('id', 'in', self.env.branches.ids)])
    commission_rate = fields.Float(
        'Commission Rate',
        default=50,
        help='Commission Rate (%) for sellers'
    )
    cycle = fields.Integer(
        'Cycle',
        help='Total cycle times, customer can use in Spa Business'
    )
    discountable = fields.Boolean(
        'Discountable',
        default=True,
        help='If it checked, not allow POS Cashier set Discount'
    )
    refundable = fields.Boolean(
        'Refundable',
        default=True,
        help='If it checked, not allow POS Cashier refund Product'
    )
    open_price = fields.Boolean(
        'Open Price Item',
        help='If it checked, when Cashier add to cart, auto ask price of this Product'
    )
    default_time = fields.Float()
    is_employee_meal = fields.Boolean('Employee Meal')

    not_returnable = fields.Boolean('Not Returnable')
    
    is_pos_bom = fields.Boolean('Is POS BoM Product?')
    is_can_be_po = fields.Boolean('Can Be Pre-Ordered')

    def add_barcode(self):
        newCode = None
        for product in self:
            format_code = "%s%s%s" % ('777', product.id, datetime.now().strftime("%d%m%y%H%M"))
            barcode = self.env['barcode.nomenclature'].sanitize_ean(format_code)
            product.write({'barcode': barcode})
            newCode = barcode
        return newCode

    def random_barcode(self):
        for product in self:
            format_code = "%s%s%s" % ('333', product.id, datetime.now().strftime("%d%m%y%H%M"))
            barcode = self.env['barcode.nomenclature'].sanitize_ean(format_code)
            product.write({'supplier_barcode': barcode})
        return True

    @api.onchange('uom_id')
    def onchange_uom_id(self):
        if self.uom_id:
            uoms = self.env['uom.uom'].search([('category_id', '=', self.uom_id.category_id.id)])
            self.uom_ids = [(6, 0, [uom.id for uom in uoms])]

    def _get_uoms_the_same_category(self):
        for product in self:
            uoms = self.env['uom.uom'].search([('category_id', '=', product.uom_id.category_id.id)])
            product.uom_ids = [(6, 0, [uom.id for uom in uoms])]

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=False, submenu=False):
        res = super(ProductTemplate, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        user_pos_not_create_edit =  self.env.user.has_group('equip3_pos_masterdata.group_pos_cashier') or self.env.user.has_group('equip3_pos_masterdata.group_pos_waiter') or self.env.user.has_group('equip3_pos_masterdata.group_pos_cooker')
        user_pos_have_create_edit =  self.env.user.has_group('equip3_pos_masterdata.group_pos_staff') or self.env.user.has_group('equip3_pos_masterdata.group_pos_supervisor') or self.env.user.has_group('equip3_pos_masterdata.group_pos_manager')
        if user_pos_not_create_edit and not user_pos_have_create_edit:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        if self.env.user.has_group('equip3_pos_masterdata.group_pos_user') and not self.env.user.has_group('equip3_pos_masterdata.group_pos_manager'):
            root = etree.fromstring(res['arch'])
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    @api.model
    def create(self, vals):
        if not vals.get('pos_branch_id'):
            vals.update({'pos_branch_id': self.env['res.branch'].sudo().get_default_branch()})
        product_tmpl = super(ProductTemplate, self).create(vals)
        products = self.env['product.product'].search([('product_tmpl_id', '=', product_tmpl.id)])
        if len(products) > 0:
            products.write_date = product_tmpl.write_date
        return product_tmpl

    def write(self, vals):
        user_pos_not_create_edit =  self.env.user.has_group('equip3_pos_masterdata.group_pos_cashier') or self.env.user.has_group('equip3_pos_masterdata.group_pos_waiter') or self.env.user.has_group('equip3_pos_masterdata.group_pos_cooker')
        user_pos_have_create_edit =  self.env.user.has_group('equip3_pos_masterdata.group_pos_staff') or self.env.user.has_group('equip3_pos_masterdata.group_pos_supervisor') or self.env.user.has_group('equip3_pos_masterdata.group_pos_manager')
        if user_pos_not_create_edit and not user_pos_have_create_edit and 'active' in vals:
            raise Warning(_("Your user not have permission to archive/active products.")) 

        res = super(ProductTemplate, self).write(vals)

        for product_temp in self:
            if product_temp.available_in_pos:
                if 'taxes_id' in vals:
                    raise UserError(_('You cannot change Tax a product saleable in point of sale while a session is still opened.'))

            products = self.env['product.product'].search([('product_tmpl_id', '=', product_temp.id)])
            for product in products:
                product.write({"write_date": product_temp.write_date,})

        return res