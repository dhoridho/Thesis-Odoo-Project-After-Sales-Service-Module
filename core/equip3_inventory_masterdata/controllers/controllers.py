# -*- coding: utf-8 -*-

from odoo import http, tools, _
from odoo.http import request
import json
import logging
from ...stock_3dview.controllers.main import ThreeDViewController

_logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class ThreeDViewController(ThreeDViewController):
    @http.route('/3dview/get_locations/tagged', type='json', auth="user", methods=['POST'])
    def get_locations(self, domain=[], **kwargs):
        domain.extend((
            ('sizex', '>', 0),
            ('sizey', '>', 0),
            ('sizez', '>', 0)
        ))
        locations = request.env['stock.location'].search(domain)
        values = []
        for location in locations:
            tags = location.tag_ids
            if tags:
                color = self._colors[tags[0].color]
                opacity = (location['occupied_percent'] * 10 / 1)
            else:
                color = '#8F8F8F'
                opacity = 500

            quant_ids = request.env['stock.quant'].with_context(inventory_mode=True).search([('location_id', '=', location.id)])
            data = []
            for quant in quant_ids:
                variant = quant.product_id.product_template_attribute_value_ids._get_combination_name()
                name = variant and "%s (%s)" % (quant.product_id.name, variant) or quant.product_id.name
                data.append({
                    'name': name,
                    'on_hand': quant.inventory_quantity,
                    'qty': quant.available_quantity,
                    'product_id': quant.product_id.id,
                    'uom_name': quant.product_uom_id.name
                })
            temp_data = []
            final_data = []
            for line in data:
                if line.get('product_id') in temp_data:
                    filter_line = list(filter(lambda r:r.get('product_id') == line.get('product_id'), final_data))
                    if filter_line:
                        filter_line[0]['qty'].append(line.get('qty'))
                        filter_line[0]['on_hand'].append(line.get('on_hand'))
                else:
                    temp_data.append(line.get('product_id'))
                    final_data.append({
                        'name': line.get('name'),
                        'on_hand': [line.get('on_hand')],
                        'qty': [line.get('qty')],
                        'product_id': line.get('product_id'),
                        'uom_name': line.get('uom_name'),
                    })
            for final_line in final_data:
                final_line['qty'] = sum(final_line['qty'])
                final_line['on_hand'] = sum(final_line['on_hand'])
            values.append( {
                'posx': location['posx'],
                'posy': location['posy'],
                'posz': location['posz'],
                'sizex': location['sizex'],
                'sizey': location['sizey'],
                'sizez': location['sizez'],
                'opacity': opacity,
                'barcode': location['barcode'],
                'color': color,
                'location': location.display_name,
                'occupied_percent': location.occupied_percent,
                'quants': final_data,
                'usage': location['usage'],
                'warehouse': location['warehouse_id']['id']
                })

        return json.dumps(values)
