# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError


class ProductTemplate(models.Model):
    _inherit = "product.template"
 
    is_online_outlet = fields.Boolean('Is Online Outlet')
    oloutlet_description = fields.Text('Description')
    oloutlet_category_id = fields.Many2one('pos.category', string='Category', domain="[('is_online_outlet','=',True)]")
    oloutlet_stock_available = fields.Boolean('Stock is Available', default=True)
    oloutlet_product_option_ids = fields.One2many('pos.online.outlet.product.option', 'oloutlet_product_tmpl_id', string='Product Options')
    oloutlet_product_image_url = fields.Char(string='GrabFood Product Image URL', compute='_compute_outlet_product_image_url')
    oloutlet_sequence = fields.Integer('Online Outlet Sequence')
    is_use_outlet_operational_hours = fields.Boolean('Use Outlet Operational Hours', default=True)
    selling_time_id = fields.Many2one('pos.online.outlet.selling.time', 'Selling Time', help='Available for GrabFood & GoFood')

    def _compute_outlet_product_image_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url.static')
        if not base_url:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for product in self:
            filename = product.name + '.' + product._get_extention()
            filename = filename.replace(' ','%20')
            url = f'{base_url}/outlets/assets/product/{product.id}/image_1920/{filename}'
            product.oloutlet_product_image_url = url

    def _get_extention(self):
        status, headers, image_base64 = self.env['ir.http'].sudo().binary_content(
        xmlid=None, model='product.template', id=self.id, field='image_128', unique=None, filename=None,
        filename_field='name', download=False, mimetype=None,
        default_mimetype='image/png', access_token=None)

        mimetype = [x[1] for x in headers if x[0] == 'Content-Type']
        mimetype = mimetype and mimetype[0] or 'image/png'
        if mimetype in ['application/octet-stream']:
            mimetype = 'image/png'
        return mimetype.split('/')[1]

    @api.model
    def create(self, values):
        if values.get('oloutlet_category_id'):
            values['is_online_outlet'] = True
            
        res = super(ProductTemplate, self).create(values)
        for product in res:
            product.set_product_online_outlet()
        return res

    def write(self, vals):
        if vals.get('oloutlet_category_id'):
            vals['is_online_outlet'] = True

        if 'oloutlet_category_id' in vals and not vals.get('oloutlet_category_id'):
            vals['is_online_outlet'] = False

        res = super(ProductTemplate, self).write(vals)
        if 'oloutlet_category_id' in vals or 'is_online_outlet' in vals:
            for product in self:
                product.set_product_online_outlet()
        return res

    def unlink(self):
        OnlineOutletOrderLine = self.env['pos.online.outlet.order.line']
        for product in self:
            product.delete_product_online_outlet()
            for variant in product.product_variant_ids:
                domain = [('product_id','=', variant.id), ('order_id','!=',False)]
                if OnlineOutletOrderLine.search_read(domain, ['id'], limit=1):
                    raise UserError(('Cannot Delete this product that is already used in the online outlet, please archived it instead. (%s)' % str(variant.name)))
        return super(ProductTemplate, self).unlink()


    def set_product_online_outlet(self):
        self.ensure_one()
        online_outlet_obj = self.env['pos.online.outlet']
        online_outlet_categ_obj = self.env['pos.online.outlet.categories']
        online_outlet_product_obj = self.env['pos.online.outlet.products']
        values_create_p = []
        if self.is_online_outlet and self.oloutlet_category_id.is_online_outlet:
            all_outlets_ids = online_outlet_obj.search([]).ids
            for outlet_id in all_outlets_ids:
                check_exist_product = online_outlet_product_obj.search([('outlet_id','=',outlet_id),('product_tmpl_id','=',self.id)],limit=1).ids
                if check_exist_product:
                    continue
                values_create_p.append({
                    'outlet_id': outlet_id,
                    'product_tmpl_id': self.id
                })
            if values_create_p:
                online_outlet_product_obj.create(values_create_p)

        else:
            self.delete_product_online_outlet()

        return True

    def delete_product_online_outlet(self):
        self.ensure_one()
        q = f'''
            DELETE FROM pos_online_outlet_products 
            WHERE product_tmpl_id = {self.id};
        '''
        self.env.cr.execute(q)

        return True


class ProductProduct(models.Model):
    _inherit = "product.product"

    def unlink(self):
        OnlineOutletOrderLine = self.env['pos.online.outlet.order.line']
        for product in self:
            domain = [('product_id','=', product.id), ('order_id','!=',False)]
            if OnlineOutletOrderLine.search_read(domain, ['id'], limit=1):
                raise UserError(('Cannot Delete this product that is already used in the online outlet, please archived it instead. (%s)' % str(product.name)))
        return super(ProductTemplate, self).unlink()