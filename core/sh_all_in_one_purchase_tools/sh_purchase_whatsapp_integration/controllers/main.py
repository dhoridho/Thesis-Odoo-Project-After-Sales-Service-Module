# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import http, _
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request, content_disposition
import re


class DownloadReport(http.Controller):

    def _document_check_access(self, model_name, document_id, access_token=None):
        document = request.env[model_name].browse([document_id])
        document_sudo = document.sudo().exists()
        if not document_sudo:
            raise MissingError(_("This document does not exist."))
        if access_token and document_sudo.report_token and access_token == document_sudo.report_token:
            return document_sudo
        else:
            raise AccessError(
                _("Sorry, you are not allowed to access this document."))

    def _show_report(self, model, report_type, report_ref, download=False):
        if report_type not in ('html', 'pdf', 'text'):
            raise UserError(_("Invalid report type: %s", report_type))
        
        report_sudo = request.env.ref(report_ref).sudo()
        
        if not isinstance(report_sudo, type(request.env['ir.actions.report'])):
            raise UserError(
            _("%s is not the reference of a report", report_ref))
        
        method_name = '_render_qweb_%s' % (report_type)
        report = getattr(report_sudo, method_name)(
        [model.id], data={'report_type': report_type})[0]
        reporthttpheaders = [
        ('Content-Type', 'application/pdf' if report_type == 'pdf' else 'text/html'),
        ('Content-Length', len(report)),
        ]
        if report_type == 'pdf' and download:
            filename = "%s.pdf" % (
            re.sub('\W+', '-', model._get_report_base_filename()))
            reporthttpheaders.append(
            ('Content-Disposition', content_disposition(filename)))
            return request.make_response(report, headers=reporthttpheaders)

    @http.route(['/download/po/<int:order_id>'], type='http', auth="public", website=True)
    def download_purchase_order(self, order_id, report_type=None, access_token=None, message=False, download=False, **kw):
        try:
            order_sudo = self._document_check_access(
                'purchase.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return '<br/><br/><center><h1><b>Oops Invalid URL! Please check URL and try again!</b></h1></center>'
        report_type = 'pdf'
        download = True
        return self._show_report(model=order_sudo, report_type=report_type, report_ref='purchase.action_report_purchase_order', download=download)
