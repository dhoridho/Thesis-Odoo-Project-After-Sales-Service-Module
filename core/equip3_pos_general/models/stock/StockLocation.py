# -*- coding: utf-8 -*-

import odoo

from odoo import fields, api, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    pos_branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    location_address_id = fields.Many2one(
        'res.partner',
        string='Location Address'
    )

    @api.model
    def create(self, vals):
        if not vals.get('pos_branch_id'):
            vals.update({'pos_branch_id': self.env['res.branch'].sudo().get_default_branch()})
        location = super(StockLocation, self).create(vals)
        return location

    def pos_update_stock_on_hand_by_location_id(self, vals={}):
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': vals['product_id'],
            'location_id': vals['location_id'],
            'inventory_quantity': vals['quantity'],
        })
        location = self.env['stock.location'].browse(vals['location_id'])
        product = self.env['product.product'].with_context({'location': location.id}).browse(vals.get('product_id'))
        return {
            'location': location.name,
            'product': product.display_name,
            'quantity': product.qty_available
        }

    def _get_child_locations(self, location_id, location_ids=[]):
        sql = '''
        with RECURSIVE cte as 
            (
              select id, name, location_id as parent_id from stock_location where id=%s
              union all
              select sl.id, sl.name, sl.location_id as parent_id from stock_location sl inner join cte on sl.location_id=cte.id
            )
            select * from cte;

        ''' % location_id
        self.env.cr.execute(sql)
        results = self.env.cr.dictfetchall()

        locations = {}
        for r in results:
            child_id = r['id']
            parent_id = r['parent_id']
            if parent_id not in locations:
                locations[parent_id] = [child_id]

            if parent_id in locations:
                locations[parent_id].append(child_id)

        for key in locations:
            for parent_id in locations:
                child_ids = locations[parent_id] 
                if key in child_ids:
                    locations[parent_id] += locations[key]
                    locations[parent_id] = list(set(locations[parent_id]))

        for parent_id in locations:
            locations[parent_id] = list(set(locations[parent_id]))

        return locations.get(location_id, [])
        
    def getStockDatasByLocationIds(self, product_ids=[], location_ids=[]):
        productHasRemovedIds = []
        stock_datas = {}

        for location_id in location_ids:
            stock_datas[location_id] = {}
            location_ids = self._get_child_locations(location_id, [])
            location_ids.append(location_id)
            if len(location_ids) == 1:
                location_ids.append(0)
            if len(product_ids) == 1:
                product_ids.append(0)
            if len(location_ids) == 0:
                continue

            if not product_ids:
                sql = "SELECT pp.id FROM product_product as pp, product_template as pt where pp.product_tmpl_id=pt.id and pt.type = 'product'"
                self.env.cr.execute(sql)
                products = self.env.cr.dictfetchall()
                product_ids = [p.get('id') for p in products if p.get('id')]
            product_ids = list(set([pid for pid in product_ids if pid]))

            for product_id in product_ids:
                if product_id in ('None', None):
                    continue
                sql = "SELECT sum(quantity - reserved_quantity) FROM stock_quant where location_id in %s AND product_id = %s"
                self.env.cr.execute(sql, (tuple(location_ids), product_id,))
                datas = self.env.cr.dictfetchall()
                stock_datas[location_id][product_id] = 0
                if datas and datas[0]:
                    if not datas[0].get('sum', None):
                        stock_datas[location_id][product_id] = 0
                    else:
                        stock_datas[location_id][product_id] = datas[0].get('sum')
                        
                    self.env.cr.execute("select id from product_product where id=%s" % product_id)
                    datas = self.env.cr.dictfetchall()
                    if len(datas) != 1 and product_id != 0:
                        productHasRemovedIds.append(product_id)
                        continue

        return stock_datas