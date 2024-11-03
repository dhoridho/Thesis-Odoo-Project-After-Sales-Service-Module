# -*- coding: utf-8 -*-
import logging
import werkzeug

from odoo import fields, models, http, SUPERUSER_ID, tools, _
from odoo.http import request
from odoo.addons.http_routing.models.ir_http import slug
from odoo.exceptions import ValidationError
from odoo.addons.pragmatic_odoo_website_order_display.controllers.main import OrderDisplay

logger = logging.getLogger(__name__)
OPG = 5


class OrderDisplay(OrderDisplay):
    # -*- coding: utf-8 -*-
    import logging
    import werkzeug

    from odoo import fields, models, http, SUPERUSER_ID, tools, _
    from odoo.http import request
    from odoo.addons.http_routing.models.ir_http import slug
    from odoo.exceptions import ValidationError
    from odoo.addons.website.controllers.main import Website

    logger = logging.getLogger(__name__)
    OPG = 5

    class OrderDisplay(Website):
        @http.route(['/page/order/display', '/page/order/display/page/<int:page>'], type='http', auth="user",
                    website=True)
        def order_display(self, page=0, search='', opg=False, domain=None, **post):
            # only order display screen access control user should access the page 'Orders'
            if not request.env.user.has_group('pragmatic_odoo_website_order_display.group_order_display_screen'):
                raise werkzeug.exceptions.NotFound()

            if domain is None:
                domain = []
            if opg:
                try:
                    opg = int(opg)
                except ValueError:
                    opg = OPG
                post["ppg"] = opg
            else:
                opg = OPG

            so = request.env['sale.order'].sudo()

            order_stages = request.env['order.stage'].sudo().search([('action_type','in',['sale','progress'])])
            domain.append(('stage_id', 'in', order_stages._ids))
            url = "/page/order/display"
            so_count = so.search_count(domain)
            pager = request.website.pager(url=url, total=so_count, page=page, step=opg, scope=7, url_args=post)
            orders = so.search(domain, limit=opg, offset=pager['offset'], order="id asc")
            # warehouses = http.request.env['stock.warehouse'].sudo().search_read(domain=[], fields=['name'])
            values = {
                'pager': pager,
                'search_count': so_count,  # common for all searchbox
                'orders': orders,
                # 'warehouses': warehouses,
                # 'wh_id': usr.warehouse_id.id
            }
            return request.render('pragmatic_odoo_website_order_display.order_display', values)

        @http.route('/order/update', type='json', auth='public')
        def order_update(self, order_id, state='sale'):
            so = request.env['sale.order'].sudo()
            order_stage = request.env['order.stage'].sudo().search([('action_type', '=', state)], limit=1)
            so.browse(order_id).update({'stage_id': order_stage.id})
            return order_id
