# -*- coding: utf-8 -*-
# Part of AppJetty. See LICENSE file for full copyright and licensing details.
import odoo
import sys
# from imp import reload
import datetime
import logging
from odoo import fields, models, api, tools
from odoo import tools
from odoo.tools.misc import formatLang
from . import amount_to_text
try:
    from num2words import num2words
except ImportError:
    logging.getLogger(__name__).warning(
        "The num2words python library is not installed, l10n_mx_edi features won't be fully available.")
    num2words = None


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.model
    def _prepare_picking(self):
        result = super(PurchaseOrder, self)._prepare_picking()
        if result:
            result.update({'report_template_id': self.partner_id and self.partner_id.report_picking_template_id and self.partner_id.report_picking_template_id.id or self.partner_id and self.partner_id.report_delivery_template_id and self.partner_id.report_delivery_template_id.id or False})
        return result

    @api.onchange('partner_id', 'company_id')
    def onchange_partner_id(self):
        res = super(PurchaseOrder, self).onchange_partner_id()
        if self.partner_id:
            self.report_template_id = self.partner_id.report_rfq_template_id and self.partner_id.report_rfq_template_id.id \
                or self.partner_id.report_po_template_id and self.partner_id.report_po_template_id.id or False
        return res

    def _prepare_invoice(self):
        invoice_vals = super(PurchaseOrder, self)._prepare_invoice()
        if invoice_vals:
            invoice_vals.update({'report_template_id': self.partner_id and self.partner_id.report_rfq_template_id and self.partner_id.report_rfq_template_id.id or self.partner_id and self.partner_id.report_po_template_id and self.partner_id.report_po_template_id.id or False})
        return invoice_vals

    @api.model
    def _default_report_template(self):
        report_obj = self.env['ir.actions.report']
        report_id = report_obj.search(
            [('model', '=', 'purchase.order'), ('report_name', '=', 'general_template.report_purchase_custom')])
        if report_id:
            report_id = report_id[0]
        else:
            report_id = report_obj.search(
                [('model', '=', 'purchase.order')])[0]
        return report_id

    @api.depends('partner_id')
    def _default_report_template1(self):
        report_obj = self.env['ir.actions.report']
        report_id = report_obj.search(
            [('model', '=', 'purchase.order'), ('report_name', '=', 'general_template.report_purchase_custom')])
        if report_id:
            report_id = report_id[0]
        else:
            report_id = report_obj.search(
                [('model', '=', 'purchase.order')])[0]
        if self.report_template_id and self.report_template_id.id < report_id.id:
            self.write(
                {'report_template_id': report_id and report_id.id or False})
        self.report_template_id = self.report_template_id or False
        self.report_template_id1 = report_id and report_id.id or False

    def print_quotation(self):
        """ Print the invoice and mark it as sent, so that we can see more
            easily the next step of the workflow
        """
        self.ensure_one()
        self.sent = True
        res = super(PurchaseOrder, self).print_quotation()
        if self.report_template_id or self.partner_id and self.partner_id.report_template_id or self.company_id and self.company_id.report_rfq_template_id:
            report_id = self.report_template_id or self.partner_id and self.partner_id.report_template_id or self.company_id and self.company_id.report_rfq_template_id
            if report_id:
                report = report_id.report_action(self)
                return report
            else:
                return res
        return res

    def _get_street(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_address_details(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_origin_date(self, origin):
        self.ensure_one()
        res = {}
        sale_obj = self.env['purchase.order']
        lang = self._context.get("lang")
        lang_obj = self.env['res.lang']
        ids = lang_obj.search([("code", "=", lang or 'en_US')])
        sale = sale_obj.search([('name', '=', origin)])
        if sale:
            timestamp = datetime.datetime.strptime(
                sale.date_order, tools.DEFAULT_SERVER_DATETIME_FORMAT)
            ts = odoo.fields.datetime.context_timestamp(self, timestamp)
            n_date = ts.strftime(ids.date_format)
            if sale:
                return n_date
        return False

    def _get_invoice_date(self):
        self.ensure_one()
        res = {}
        sale_obj = self.env['purchase.order']
        lang = self._context.get("lang")
        lang_obj = self.env['res.lang']
        ids = lang_obj.search([("code", "=", lang or 'en_US')])
        if self.date_invoice:
            timestamp = datetime.datetime.strptime(
                self.date_invoice, tools.DEFAULT_SERVER_DATE_FORMAT)
            ts = odoo.fields.Datetime.context_timestamp(self, timestamp)
            n_date = ts.strftime(ids.date_format)
            if self:
                return n_date
        return False

    def _get_invoice_due_date(self):
        self.ensure_one()
        res = {}
        sale_obj = self.env['purchase.order']
        lang = self._context.get("lang")
        lang_obj = self.env['res.lang']
        ids = lang_obj.search([("code", "=", lang or 'en_US')])
        if self.date_due:
            timestamp = datetime.datetime.strptime(
                self.date_due, tools.DEFAULT_SERVER_DATE_FORMAT)
            ts = odoo.fields.Datetime.context_timestamp(self, timestamp)
            n_date = ts.strftime(ids.date_format)
            if self:
                return n_date
        return False

    def _get_tax_amount(self, amount):
        self.ensure_one()
        res = {}
        currency = self.currency_id or self.company_id.currency_id
        res = formatLang(self.env, amount, currency_obj=currency)
        return res

    @api.depends('amount_total')
    def _amount_in_words(self):
        for obj in self:
            if obj.partner_id.lang == 'nl_NL':
                obj.amount_to_text = amount_to_text.amount_to_text_nl(
                    obj.amount_total, currency='euro')
            else:
                try:
                    if obj.partner_id.lang:
                        obj.amount_to_text = num2words(
                            obj.amount_total, lang=obj.partner_id.lang).title()
                    else:
                        obj.amount_to_text = num2words(
                            obj.amount_total, lang='en').title()
                except NotImplementedError:
                    obj.amount_to_text = num2words(
                        obj.amount_total, lang='en').title()

    report_template_id1 = fields.Many2one('ir.actions.report', string="Purchase Template1", compute='_default_report_template1',
                                          help="Please select Template report for Purchase Order", domain=[('model', '=', 'purchase.order')])
    report_template_id = fields.Many2one('ir.actions.report', string="Purchase Template",
                                         help="Please select Template report for Purchase Order", domain=[('model', '=', 'purchase.order')])
    amount_to_text = fields.Char(compute='_amount_in_words',
                                 string='In Words', help="The amount in words")
