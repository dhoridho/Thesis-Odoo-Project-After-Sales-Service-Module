# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd.
# - © Technaureus Info Solutions Pvt. Ltd 2019. All rights reserved.

from odoo import http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager


class PortalAccount(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(PortalAccount, self)._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        BookingBooking = request.env['booking.booking']
        booking_count = BookingBooking.search_count([
            ('partner_id', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['draft', 'confirm', 'cancel'])
        ])
        values.update({
            'booking_count': booking_count,
        })
        return values

    def _booking_get_page_view_values(self, booking, access_token, **kwargs):
        values = {
            'page_name': 'booking',
            'booking': booking,
        }
        return self._get_page_view_values(booking, access_token, values, 'my_bookings_history', False, **kwargs)

    @http.route(['/my/bookings', '/my/bookings/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_bookings(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        booking = request.env['booking.booking']
        domain = [
            ('partner_id', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['draft', 'confirm', 'cancel'])
        ]
        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        archive_groups = self._get_archive_groups('booking.booking', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
        booking_count = booking.search_count(domain)
        pager = portal_pager(
            url="/my/bookings",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=booking_count,
            page=page,
            step=self._items_per_page
        )
        bookings = booking.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_bookings_history'] = bookings.ids[:100]

        values.update({
            'date': date_begin,
            'date_end': date_end,
            'bookings': bookings.sudo(),
            'page_name': 'booking',
            'archive_groups': archive_groups,
            'default_url': '/my/bookings',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby
        })
        return request.render("tis_venue_booking.portal_my_bookings", values)

    @http.route(['/my/bookings/<int:booking_id>'], type='http', auth="public", website=True)
    def portal_my_booking(self, booking_id=None, access_token=None, report_type=None, download=False, **kw):
        try:
            booking_sudo = self._document_check_access('booking.booking', booking_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=booking_sudo, report_type=report_type,
                                     report_ref='tis_venue_booking.action_report_booking_order', download=download)
        values = self._booking_get_page_view_values(booking_sudo, access_token, **kw)
        return request.render("tis_venue_booking.portal_my_booking", values)
