# -*- coding: utf-8 -*-

from odoo import http, fields, _
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import AccessError, MissingError
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo import fields as odoo_fields, http, tools, _, SUPERUSER_ID
import base64


class HMSPortal(CustomerPortal):
    def _prepare_portal_layout_values(self):
        values = super(HMSPortal, self)._prepare_portal_layout_values()
        consent_form_count = 0
        if request.env['acs.consent.form'].check_access_rights('read', raise_exception=False):
            consent_form_count = request.env['acs.consent.form'].search_count([('state','!=','draft')])

        values.update({
            'consent_form_count': consent_form_count,
        })
        return values

    @http.route(['/my/consentforms', '/my/consentforms/page/<int:page>'], type='http', auth="user", website=True)
    def my_consent_forms(self, page=1, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        user = request.env.user
        if not sortby:
            sortby = 'date'

        sortings = {
            'date': {'label': _('Newest'), 'order': 'date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }

        order = sortings.get(sortby, sortings['date'])['order']
 
        pager = portal_pager(
            url="/my/consentforms",
            url_args={},
            total=values['consent_form_count'],
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        consent_forms = request.env['acs.consent.form'].search([('state','!=','draft')],
            order=order, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'sortings': sortings,
            'sortby': sortby,
            'consent_forms': consent_forms,
            'page_name': 'consent_form',
            'default_url': '/my/consentforms',
            'searchbar_sortings': sortings,
            'pager': pager
        })
        return request.render("acs_consent_form.my_consent_forms", values)

    @http.route(['/my/consentforms/<int:consent_form_id>'], type='http', auth="public", website=True)
    def my_consent_form_data(self, consent_form_id=None, access_token=None, report_type=None, message=False, download=False, **kw):
        try:
            order_sudo = self._document_check_access('acs.consent.form', consent_form_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if report_type in ('html', 'pdf', 'text'):
           return self._show_report(model=order_sudo, report_type=report_type,report_ref='acs_consent_form.report_acs_consent_form',download=download)

        values = {
            'consent_form': order_sudo,
            'message': message,
            'action': order_sudo._get_portal_return_action(),
        }
        return request.render("acs_consent_form.my_consent_form", values)

    @http.route(['/my/consentform/<int:consent_form_id>/sign'], type='json', auth="public", website=True)
    def acs_portal_document_sign(self, consent_form_id, access_token=None, name=None, signature=None):
        # get from query string if not on json param
        access_token = access_token or request.httprequest.args.get('access_token')
        try:
            order_sudo = self._document_check_access('acs.consent.form', consent_form_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if not signature:
            return {'error': _('Signature is missing.')}

        try:
            order_sudo.write({
                'acs_signed_on': fields.Datetime.now(),
                'acs_signature': signature,
                'acs_has_to_be_signed': False,
            })
            order_sudo.action_signed()
        except (TypeError, binascii.Error) as e:
            return {'error': _('Invalid signature data.')}

        _message_post_helper(
            'acs.consent.form', order_sudo.id, _('Declaration signed by %s') % (name,),
            **({'token': access_token} if access_token else {}))

        return {
            'force_refresh': True,
            'redirect_url': '/my/consentforms/%s?message=sign_ok&access_token=%s' %(order_sudo.id, access_token),
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: