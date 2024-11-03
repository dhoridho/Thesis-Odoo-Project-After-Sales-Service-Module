# -*- coding: utf-8 -*
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_repr
from random import choice
from string import digits
from lxml import etree


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    barcode = fields.Char('Barcode')



    def generate_pricelist_report(self):
        all_data = ""
        product_data = {}
        for line in self.item_ids:
            if line.product_tmpl_id.id in product_data:
                get_data = product_data.get(line.product_tmpl_id.id)
                temp_data = {}
                temp_data['name'] = line.product_tmpl_id.name
                temp_data['fixed_price'] = line.fixed_price
                temp_data['min_quantity'] = line.min_quantity
                temp_data['uom'] = line.product_tmpl_id.uom_id.name
                temp_data['currency'] = self.env.company.currency_id.symbol
                temp_data['price'] = line.minimum_price * line.min_quantity
                get_data.append(temp_data)
                product_data.update({line.product_tmpl_id.id:get_data})
            else:
                get_data = []
                temp_data = {}
                temp_data['fixed_price'] = line.fixed_price or 0
                temp_data['min_quantity'] = line.min_quantity
                temp_data['uom'] = line.product_tmpl_id.uom_id.name
                temp_data['currency'] = self.env.company.currency_id.symbol
                temp_data['price'] = line.minimum_price * line.min_quantity
                get_data.append(temp_data)
                product_data.update({line.product_tmpl_id.id: get_data})

        for dt in product_data:
            product_obj = self.env['product.template'].browse(dt)
            all_data += "</br><table width='50%'><thead>"+str(product_obj.name).upper()+"</thead><tbody>"

            tbody = ""

            cnt = 0
            for data in product_data.get(dt):
                if cnt==0:
                    tbody += "<tr><td align='left'>" + str(product_obj.list_price) + " / 1" + data.get('uom') + "</td></tr>"
                    cnt += 1

                upd_price = data.get('fixed_price') * data.get('min_quantity')
                tbody += "<tr><td align='left'>" + str(upd_price)+' / '+str(data.get('min_quantity'))+data.get('uom')+"</td></tr>"
            tbody += "</tbody></table>"
            all_data += tbody
        return all_data

    def generate_random_barcode(self):
        for user in self:
            user.barcode = self.env['barcode.nomenclature'].sanitize_ean('074' + "".join(choice(digits) for i in range(9)))
            print (user.barcode)

    def write(self, vals):
        res = super(ProductPricelist, self).write(vals)
        if self._name == 'product.pricelist':
            self.env['pos.cache.database'].request_pos_sessions_online_reload_by_channel('pos.sync.pricelists')
        return res

    def unlink(self):
        if self._name == 'product.pricelist':
            for pricelist in self:
                orders = self.env['pos.order'].sudo().search([
                    ('pricelist_id', '=', pricelist.id)
                ], limit=1)
                if orders:
                    raise UserError('%s Used have save on many POS Orders, not allow remove it' % pricelist.name)
                pos_configs = self.env['pos.config'].sudo().search([
                    ('pricelist_id', '=', pricelist.id)
                ], limit=1)
                if pos_configs:
                    raise UserError('%s Used have used for POS Config, could not allow remove it' % pricelist.name)
                pos_sessions = self.env['pos.session'].sudo().search([
                    ('state', '=', 'opened')
                ], limit=1)
                if pos_sessions:
                    raise UserError('Please close all POS session before remove Pricelist')
        res = super(ProductPricelist, self).unlink()
        if self._name == 'product.pricelist':
            self.env['pos.cache.database'].request_pos_sessions_online_reload_by_channel('pos.sync.pricelists')
        return res

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=False, submenu=False):
        res = super(ProductPricelist, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        if self.env.user.has_group('equip3_pos_masterdata.group_pos_user') and not self.env.user.has_group('equip3_pos_masterdata.group_pos_manager'):
            root = etree.fromstring(res['arch'])
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    uom_id = fields.Many2one('uom.uom', 'Unit of Measure')
    uom_ids = fields.Many2many('uom.uom', string='Units the same category', compute='_get_uoms_the_same_category')
    applied_on = fields.Selection(selection_add=[
        ('4_pos_category', 'POS Category'),
    ], ondelete={
        '4_pos_category': 'set default',
    })
    pos_category_id = fields.Many2one('pos.category', 'POS Category')
    min_price = fields.Float(
        'Min Price',
        help='Not allow POS Users set price smaller than it'
    )
    max_price = fields.Float(
        'Max Price',
        help='Not allow POS Users set price bigger than it'
    )
    name = fields.Char(compute='_get_pricelist_item_name_price')


    @api.depends('applied_on', 'categ_id', 'product_tmpl_id', 'product_id', 'compute_price', 'fixed_price', \
        'pricelist_id', 'percent_price', 'price_discount', 'price_surcharge')
    def _get_pricelist_item_name_price(self):
        res = super(ProductPricelistItem, self)._get_pricelist_item_name_price()
        for item in self:
            if item.pos_category_id and item.applied_on == '4_pos_category':
                item.name = _("POS Category: %s") % (item.pos_category_id.display_name)

                if item.compute_price == 'fixed':
                    decimal_places = self.env['decimal.precision'].precision_get('Product Price')
                    if item.currency_id.position == 'after':
                        item.price = "%s %s" % (
                            float_repr(
                                item.fixed_price,
                                decimal_places,
                            ),
                            item.currency_id.symbol,
                        )
                    else:
                        item.price = "%s %s" % (
                            item.currency_id.symbol,
                            float_repr(
                                item.fixed_price,
                                decimal_places,
                            ),
                        )
                elif item.compute_price == 'percentage':
                    item.price = _("%s %% discount", item.percent_price)
                else:
                    item.price = _("%(percentage)s %% discount and %(price)s surcharge", percentage=item.price_discount, price=item.price_surcharge)

    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id
            uoms = self.env['uom.uom'].search([('category_id', '=', self.product_id.uom_id.category_id.id)])
            self.uom_ids = [(6, 0, [uom.id for uom in uoms])]

    def _get_uoms_the_same_category(self):
        for item in self:
            if item.product_id:
                uoms = self.env['uom.uom'].search([('category_id', '=', item.product_id.uom_id.category_id.id)])
                item.uom_ids = [(6, 0, [uom.id for uom in uoms])]
            else:
                item.uom_ids = [(6, 0, [])]
    @api.model
    def create(self, vals):
        res = super(ProductPricelistItem, self).create(vals)
        if self._name == 'product.pricelist.item':
            self.env['pos.cache.database'].request_pos_sessions_online_reload_by_channel('pos.sync.pricelists')
        return res

    def write(self, vals):
        res = super(ProductPricelistItem, self).write(vals)
        if self._name == 'product.pricelist.item':
            self.env['pos.cache.database'].request_pos_sessions_online_reload_by_channel('pos.sync.pricelists')
        return res

    def unlink(self):
        if self._name == 'product.pricelist.item':
            self.env['pos.cache.database'].request_pos_sessions_online_reload_by_channel('pos.sync.pricelists')
        return super(ProductPricelistItem, self).unlink()
