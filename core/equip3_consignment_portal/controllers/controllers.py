
from collections import OrderedDict
from odoo import http, _
from odoo.http import request
from odoo.osv.expression import OR
from ...odoo_consignment_process.controllers.main import CustomerPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager

class CustomerPortal(CustomerPortal):

    @http.route(['/my/consignment_owner', '/my/consignment_owner/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_consignment_owner(self, page=1, filterby=None, sortby=None, search=None, search_in='content', **kw):
        res = super().portal_my_consignment_owner(page=page, filterby=filterby, sortby=sortby, search=search, search_in=search_in, **kw)
        return request.render("equip3_consignment_portal.consignment_owner_page", res.qcontext)

    @http.route(['/my/consignment_owner/<int:order>'], type='http', auth="user", website=True)
    def my_consignment_picking_detail(self, order=None, **kw):
        purchase_order = request.env['purchase.order'].sudo().browse(order)
        return request.render("odoo_consignment_process.display_my_consignment_detail_consignment", {'order': purchase_order})

    @http.route(['/my/consignment_stock', '/my/consignment_stock/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_consignment_stock(self, page=1, step=20, filterby=None, sortby=None, search=None, search_in='content', **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        domain = [('owner_id', '=', partner.id)]
        stock_quant_count = request.env['stock.quant'].sudo().search_count(domain)
        pager = portal_pager(
            url="/my/consignment_stock",
            total=stock_quant_count,
            page=page,
            step=step,
        )
        stock_quant_ids = request.env['stock.quant'].sudo().search(domain, limit=self._items_per_page, offset=pager['offset'])
        values.update({
            'stock_quant_ids' : stock_quant_ids,
            'page_name': 'consignment_stock',
            'pager': pager,
            'default_url': '/my/consignment_stock',
        })
        return request.render("equip3_consignment_portal.portal_my_consignment_stock", values)
    
    def _prepare_portal_layout_values(self):
        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        stock_quant_ids = request.env['stock.quant'].sudo().search_count([('owner_id', '=', partner.id)])
        values['stock_quant_ids'] = stock_quant_ids
        return values

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        portal_values = self._prepare_portal_layout_values()
        if 'stock_quant_ids' in counters:
            values['stock_quant_ids'] = portal_values['stock_quant_ids']
        return values
