# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from collections import OrderedDict
from dateutil.relativedelta import relativedelta
from operator import itemgetter

from odoo import fields, http, _
from odoo.http import request
from odoo.tools import date_utils, groupby as groupbyelem
from odoo.osv.expression import AND

from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class ShPickingCustomerPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):

        values = super(ShPickingCustomerPortal,
                       self)._prepare_portal_layout_values()
        picking_obj = request.env['stock.picking']
        pickings = picking_obj.sudo().search(
            [('partner_id', '=', request.env.user.partner_id.id)])
        picking_count = picking_obj.sudo().search_count(
            [('partner_id', '=', request.env.user.partner_id.id)])
        values['picking_count'] = picking_count
        values['pickings'] = pickings
        return values

    @http.route(['/my/pickings', '/my/pickings/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_picking(self, page=1, sortby=None, filterby=None, search=None, search_in='all', groupby='none', **kw):
        Picking_sudo = request.env['stock.picking'].sudo()
        values = self._prepare_portal_layout_values()
        searchbar_sortings = {
            'scheduled_date': {'label': _('Newest'), 'order': 'scheduled_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }
        searchbar_inputs = {
            'all': {'input': 'all', 'label': _('Search in All')},
        }

        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'type': {'input': 'type', 'label': _('Picking Type')},
            'status': {'input': 'status', 'label': _('Status')},
            'source': {'input': 'source', 'label': _('Source Document')},
            'responsible': {'input': 'responsible', 'label': _('Responsible')},
        }

        today = fields.Date.today()
        quarter_start, quarter_end = date_utils.get_quarter(today)
        last_week = today + relativedelta(weeks=-1)
        last_month = today + relativedelta(months=-1)
        last_year = today + relativedelta(years=-1)

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'today': {'label': _('Today'), 'domain': [("scheduled_date", "=", today)]},
            'week': {'label': _('This week'), 'domain': [('scheduled_date', '>=', date_utils.start_of(today, "week")), ('scheduled_date', '<=', date_utils.end_of(today, 'week'))]},
            'month': {'label': _('This month'), 'domain': [('scheduled_date', '>=', date_utils.start_of(today, 'month')), ('scheduled_date', '<=', date_utils.end_of(today, 'month'))]},
            'year': {'label': _('This year'), 'domain': [('scheduled_date', '>=', date_utils.start_of(today, 'year')), ('scheduled_date', '<=', date_utils.end_of(today, 'year'))]},
            'quarter': {'label': _('This Quarter'), 'domain': [('scheduled_date', '>=', quarter_start), ('scheduled_date', '<=', quarter_end)]},
            'last_week': {'label': _('Last week'), 'domain': [('scheduled_date', '>=', date_utils.start_of(last_week, "week")), ('scheduled_date', '<=', date_utils.end_of(last_week, 'week'))]},
            'last_month': {'label': _('Last month'), 'domain': [('scheduled_date', '>=', date_utils.start_of(last_month, 'month')), ('scheduled_date', '<=', date_utils.end_of(last_month, 'month'))]},
            'last_year': {'label': _('Last year'), 'domain': [('scheduled_date', '>=', date_utils.start_of(last_year, 'year')), ('scheduled_date', '<=', date_utils.end_of(last_year, 'year'))]},
        }
        # default sort by value
        if not sortby:
            sortby = 'scheduled_date'
        order = searchbar_sortings[sortby]['order']
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain = AND([searchbar_filters[filterby]['domain']])

        if search and search_in:
            domain = AND([domain, [('name', 'ilike', search)]])
        domain = AND(
            [domain, [('partner_id', '=', request.env.user.partner_id.id)]])
        picking_count = Picking_sudo.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/pickings",
            url_args={'sortby': sortby, 'search_in': search_in,
                      'search': search, 'filterby': filterby},
            total=picking_count,
            page=page,
            step=self._items_per_page
        )

        if groupby == 'type':
            order = "picking_type_id, %s" % order
        elif groupby == 'status':
            order = "state, %s" % order
        elif groupby == 'source':
            order = "origin, %s" % order
        elif groupby == 'responsible':
            order = "user_id, %s" % order
        pickings = Picking_sudo.search(
            domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        if groupby == 'type':
            grouped_pickings = [Picking_sudo.concat(
                *g) for k, g in groupbyelem(pickings, itemgetter('picking_type_id'))]
        elif groupby == 'status':
            grouped_pickings = [Picking_sudo.concat(
                *g) for k, g in groupbyelem(pickings, itemgetter('state'))]
        elif groupby == 'source':
            grouped_pickings = [Picking_sudo.concat(
                *g) for k, g in groupbyelem(pickings, itemgetter('origin'))]
        elif groupby == 'responsible':
            grouped_pickings = [Picking_sudo.concat(
                *g) for k, g in groupbyelem(pickings, itemgetter('user_id'))]
        else:
            grouped_pickings = [pickings]
        values.update({
            'pickings': pickings,
            'grouped_pickings': grouped_pickings,
            'page_name': 'picking',
            'default_url': '/my/pickings',
            'picking_count': picking_count,
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'search_in': search_in,
            'sortby': sortby,
            'groupby': groupby,
            'searchbar_inputs': searchbar_inputs,
            'searchbar_groupby': searchbar_groupby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
        })
        return request.render("sh_portal_picking.picking_my_picking", values)

    @http.route(['/my/pickings/<int:picking_id>'], type='http', auth="public", website=True)
    def portal_my_pickings_form(self, picking_id, report_type=None, access_token=None, message=False, download=False, **kw):
        picking_sudo = self._document_check_access('stock.picking', picking_id)
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=picking_sudo, report_type=report_type, report_ref='stock.action_report_delivery', download=download)
        values = {
            'token': access_token,
            'picking': picking_sudo,
            'message': message,
            'bootstrap_formatting': True,
            'partner_id': picking_sudo.partner_id.id,
            'report_type': 'html',
        }
        return request.render('sh_portal_picking.portal_picking_form_template', values)
