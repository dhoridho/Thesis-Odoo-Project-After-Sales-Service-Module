from odoo import http, _
from odoo.http import request
from odoo.exceptions import AccessError, MissingError
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class CustomerPortalExtended(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id

        # Add service request count
        if 'service_request_count' in counters:
            service_request_count = request.env['service.request'].search_count([
                ('partner_id', '=', partner.id)
            ])
            values['service_request_count'] = service_request_count

        # Add warranty claim count
        if 'warranty_claim_count' in counters:
            warranty_claim_count = request.env['warranty.claim'].search_count([
                ('partner_id', '=', partner.id)
            ])
            values['warranty_claim_count'] = warranty_claim_count

        return values

    # Service Requests
    @http.route(['/my/service-requests', '/my/service-requests/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_service_requests(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        ServiceRequest = request.env['service.request']

        domain = [('partner_id', '=', partner.id)]

        # Sorting options
        searchbar_sortings = {
            'date': {'label': _('Request Date'), 'order': 'request_date desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'status': {'label': _('Status'), 'order': 'state'},
        }

        # Default sort by date
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        # Count for pager
        service_request_count = ServiceRequest.search_count(domain)

        # Pager
        pager = portal_pager(
            url="/my/service-requests",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=service_request_count,
            page=page,
            step=self._items_per_page
        )

        # Content
        service_requests = ServiceRequest.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'service_requests': service_requests,
            'page_name': 'service_request',
            'pager': pager,
            'default_url': '/my/service-requests',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("after_sales_service.portal_my_service_requests", values)

    @http.route(['/my/service-requests/<int:service_request_id>'], type='http', auth="user", website=True)
    def portal_my_service_request(self, service_request_id=None, access_token=None, **kw):
        try:
            service_request_sudo = self._document_check_access('service.request', service_request_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = {
            'service_request': service_request_sudo,
            'page_name': 'service_request',
        }
        return request.render("after_sales_service.portal_my_service_request", values)

    # Warranty Claims
    @http.route(['/my/warranty-claims', '/my/warranty-claims/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_warranty_claims(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        WarrantyClaim = request.env['warranty.claim']

        domain = [('partner_id', '=', partner.id)]

        # Sorting options
        searchbar_sortings = {
            'date': {'label': _('Claim Date'), 'order': 'claim_date desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'status': {'label': _('Status'), 'order': 'state'},
        }

        # Default sort by date
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        # Count for pager
        warranty_claim_count = WarrantyClaim.search_count(domain)

        # Pager
        pager = portal_pager(
            url="/my/warranty-claims",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=warranty_claim_count,
            page=page,
            step=self._items_per_page
        )

        # Content
        warranty_claims = WarrantyClaim.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'warranty_claims': warranty_claims,
            'page_name': 'warranty_claim',
            'pager': pager,
            'default_url': '/my/warranty-claims',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("after_sales_service.portal_my_warranty_claims", values)

    @http.route(['/my/warranty-claims/<int:warranty_claim_id>'], type='http', auth="user", website=True)
    def portal_my_warranty_claim(self, warranty_claim_id=None, access_token=None, **kw):
        try:
            warranty_claim_sudo = self._document_check_access('warranty.claim', warranty_claim_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = {
            'warranty_claim': warranty_claim_sudo,
            'page_name': 'warranty_claim',
        }
        return request.render("after_sales_service.portal_my_warranty_claim", values)