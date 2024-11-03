# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import numpy as np

class PosCategory(models.Model):
    _inherit = "pos.category"

    is_online_outlet = fields.Boolean('Is Online Outlet')
    selling_time_id = fields.Many2one('pos.online.outlet.selling.time', 'Selling Time', help='Available for GrabFood')
    is_use_outlet_operational_hours = fields.Boolean('Use Outlet Operational Hours', default=True)

    @api.model
    def create(self, values):
        res = super(PosCategory, self).create(values)
        for category in res:
            category.set_category_online_outlet()
        return res

    def write(self, vals):
        res = super(PosCategory, self).write(vals)
        if 'is_online_outlet' in vals:
            for category in self:
                category.set_category_online_outlet()
        return res

    def unlink(self):
        for category in self:
            category.delete_category_online_outlet()
        return super(PosCategory, self).unlink()

    def set_category_online_outlet(self):
        self.ensure_one()
        online_outlet_obj = self.env['pos.online.outlet']
        online_outlet_categ_obj = self.env['pos.online.outlet.categories']
        online_outlet_product_obj = self.env['pos.online.outlet.products']
        if self.is_online_outlet:
            all_outlets_ids = online_outlet_obj.search([]).ids
            values_create = []
            values_create_p = []
            all_product_ids = self.env['product.template'].search([('is_online_outlet','=',True),('oloutlet_category_id','=',self.id)]).ids
            for outlet_id in all_outlets_ids:
                outlet_id = outlet_id
                for product_id in all_product_ids:
                    check_exist_product = online_outlet_product_obj.search([('outlet_id','=',outlet_id),('product_tmpl_id','=',product_id)],limit=1).ids
                    if check_exist_product:
                        continue
                    values_create_p.append({
                        'outlet_id': outlet_id,
                        'product_tmpl_id': product_id
                    })
                values = {
                    'outlet_id': outlet_id,
                    'pos_categ_id': self.id
                }
                values_create.append(values)
            if values_create:
                online_outlet_categ_obj.create(values_create)
            if values_create_p:
                online_outlet_product_obj.create(values_create_p)


        else:
            self.delete_category_online_outlet()

        return True

    def delete_category_online_outlet(self):
        self.ensure_one()
        q = f'''
            DELETE FROM pos_online_outlet_categories 
            WHERE pos_categ_id = {self.id};
            DELETE FROM pos_online_outlet_products 
            WHERE pos_categ_id = {self.id};
        '''
        self.env.cr.execute(q)

        return True