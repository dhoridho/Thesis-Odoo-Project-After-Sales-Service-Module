# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

import base64
from collections import OrderedDict
from odoo import http
from odoo.http import request
from odoo.tools import image_process
from odoo.tools.translate import _
from odoo.addons.portal.controllers.portal import pager as portal_pager, CustomerPortal
from odoo.addons.web.controllers.main import Binary


class PurchaseRFQPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(PurchaseRFQPortal, self)._prepare_portal_layout_values()
        values['rfq_count'] = request.env['purchase.order'].search_count([
            ('state', 'in', ['draft', 'sent']), ('partner_id',
                                                 '=', request.env.user.partner_id.id)
        ])
        return values

    def _rfq_order_get_page_view_values(self, quotes, access_token, **kwargs):
        #
        def resize_to_48(b64source):
            if not b64source:
                b64source = base64.b64encode(Binary().placeholder())
            return image_process(b64source, size=(48, 48))

        values = {
            'quotes': quotes,
            'resize_to_48': resize_to_48,
        }
        return self._get_page_view_values(quotes, access_token, values, 'my_quotes_history', True, **kwargs)

    @http.route(['/my/rfq', '/my/rfq/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_rfq(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        PurchaseOrder = request.env['purchase.order']

        domain = []

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin),
                       ('create_date', '<=', date_end)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc, id desc'},
            'name': {'label': _('Name'), 'order': 'name asc, id asc'},
            'amount_total': {'label': _('Total'), 'order': 'amount_total desc, id desc'},
        }
        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': [('state', 'in', ['draft', 'sent']), ('partner_id', '=', request.env.user.partner_id.id)]},
            'draft': {'label': _('Request For Quotation'), 'domain': [('state', '=', 'draft'), ('partner_id', '=', request.env.user.partner_id.id)]},
            'sent': {'label': _('Sent'), 'domain': [('state', 'in', ['sent']), ('partner_id', '=', request.env.user.partner_id.id)]},
        }
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        # count for pager
        rfq_count = PurchaseOrder.search_count(domain)
        # make pager
        pager = portal_pager(
            url="/my/rfq",
            url_args={'date_begin': date_begin, 'date_end': date_end},
            total=rfq_count,
            page=page,
            step=self._items_per_page
        )
        # search the purchase orders to display, according to the pager data
        rfqs = PurchaseOrder.sudo().search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )
        request.session['my_quotes_history'] = rfqs.ids[:100]

        values.update({
            'date': date_begin,
            'rfqs': rfqs,
            'page_name': 'quotes',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
            'default_url': '/my/rfq',
        })
        return request.render("sh_rfq_portal.sh_portal_my_rfqs", values)

    @http.route(['/my/rfq/<int:quote_id>'], type='http', auth="user", website=True)
    def portal_my_rfq_form(self, quote_id, report_type=None, access_token=None, message=False, download=False, **kw):
        quote_sudo = request.env['purchase.order'].sudo().browse(quote_id)
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=quote_sudo, report_type=report_type, report_ref='purchase.report_purchase_quotation', download=download)
        values = {
            'token': access_token,
            'quotes': quote_sudo,
            'message': message,
            'bootstrap_formatting': True,
            'partner_id': quote_sudo.partner_id.id,
            'report_type': 'html',
        }
        return request.render('sh_rfq_portal.portal_rfq_form_template', values)

    @http.route(['/my/rfq/update/<int:quote_id>'], type='http', auth="user", website=True)
    def portal_my_rfqs_update(self, quote_id=None, report_type=None, access_token=None, message=False, download=False, **kw):
        quote_sudo = request.env['purchase.order'].sudo().browse(quote_id)
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=quote_sudo, report_type=report_type, report_ref='purchase.report_purchase_quotation', download=download)
        values = {
            'token': access_token,
            'quotes': quote_sudo,
            'message': message,
            'bootstrap_formatting': True,
            'partner_id': quote_sudo.partner_id.id,
            'report_type': 'html',
        }
        return request.render("sh_rfq_portal.sh_portal_my_rfq_order_update", values)

    @http.route(['/rfq/update'], type='http', auth="user", website=True, csrf=False)
    def custom_rfq_update(self, access_token=None, **kw):
        if kw.get('order_id'):
            purchase_order = request.env['purchase.order'].sudo().search(
                [('id', '=', kw.get('order_id'))], limit=1)
            if purchase_order:
                if purchase_order.order_line:
                    for k, v in kw.items():
                        if k != 'order_id' and '_' not in k and k!='rfq_note':
                            purchase_order_line = request.env['purchase.order.line'].sudo().search(
                                [('order_id', '=', purchase_order.id), ('id', '=', k)], limit=1)
                            if purchase_order_line:
                                price = v
                                if ',' in price:
                                    price = price.replace(",", ".")
                                purchase_order_line.sudo().write({
                                    'price_unit':float(price),
                                    })
                        if k != 'order_id' and '_' in k and k!='rfq_note':
                            order_line = k.split("_note")
                            purchase_order_line = request.env['purchase.order.line'].sudo().search(
                                [('order_id', '=', purchase_order.id), ('id', '=', int(order_line[0]))], limit=1)
                            if purchase_order_line:
                                note = v
                                purchase_order_line.sudo().write({
                                    'sh_tender_note':note,
                                    })
                        if k=='rfq_note':
                            note = kw.get(k)
                            purchase_order.sudo().write({
                                'notes':note
                                })
        url = '/my/rfq/update/'+str(kw.get('order_id'))
        return request.redirect(url)

    @http.route(['/rfq/edit'], type='http', auth="user", website=True, csrf=False)
    def custom_rfq_edit(self, **kw):
        url = '/my/rfq/'+str(kw.get('order_id'))
        return request.redirect(url)
