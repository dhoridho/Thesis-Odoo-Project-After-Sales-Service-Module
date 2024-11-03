# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo import SUPERUSER_ID
from datetime import date, time, datetime
from odoo.osv import expression
from odoo.tools import float_is_zero
import uuid
import hashlib
import hmac
from werkzeug.urls import url_encode

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    access_url = fields.Char(
        'Portal Access URL', compute='_compute_access_url',
        help='Customer Portal URL')

    access_token = fields.Char('Security Token', copy=False)
    user_id = fields.Many2one('res.users', string='Salesperson', index=True, tracking=2, default=lambda self: self.env.user)

    @api.model
    def create(self, vals):
        res = super(StockPicking, self).create(vals)
        stock_picking = self.env['stock.picking'].search([('name','=',vals['name'])])
        sale_order = self.env['sale.order'].search([('name','=',stock_picking.origin)],limit=1)
        purchase_order = self.env['purchase.order'].search([('name','=',stock_picking.origin)],limit=1)
        if sale_order:
            stock_picking.write({'user_id':sale_order.user_id.id})
        if purchase_order:
            stock_picking.write({'user_id':purchase_order.user_id.id})
        return res
    
    def _compute_access_url(self):
        for record in self:
            record.access_url = ''

    def _portal_ensure_token(self):
        """ Get the current record access token """
        if not self.access_token:
            # we use a `write` to force the cache clearing otherwise `return self.access_token` will return False
            self.sudo().write({'access_token': str(uuid.uuid4())})
        return self.access_token

    def _get_report_base_filename(self):
        self.ensure_one()
        return '%s %s' % (self.name, self.name)

    def get_portal_url(self, suffix=None, report_type=None, download=None, query_string=None, anchor=None):
        """
            Get a portal url for this model, including access_token.
            The associated route must handle the flags for them to have any effect.
            - suffix: string to append to the url, before the query string
            - report_type: report_type query string, often one of: html, pdf, text
            - download: set the download query string to true
            - query_string: additional query string
            - anchor: string to append after the anchor #
        """
        self.ensure_one()
        url = self.access_url + '%s?access_token=%s%s%s%s%s' % (
            suffix if suffix else '',
            self._portal_ensure_token(),
            '&report_type=%s' % report_type if report_type else '',
            '&download=true' if download else '',
            query_string if query_string else '',
            '#%s' % anchor if anchor else ''
        )
        return url

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: