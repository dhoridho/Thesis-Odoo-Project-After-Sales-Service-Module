# -*- coding: utf-8 -*-
# Part of AppJetty. See LICENSE file for full copyright and licensing details.
import odoo
import sys
# from imp import reload
from datetime import datetime,timedelta
import logging
from lxml import etree
import json as simplejson
from odoo import fields, models, api, tools, _
from odoo import tools
from odoo.tools.misc import formatLang
from . import amount_to_text
try:
    from num2words import num2words
except ImportError:
    logging.getLogger(__name__).warning(
        "The num2words python library is not installed, l10n_mx_edi features won't be fully available.")
    num2words = None


class BlanketOrder(models.Model):
    _inherit = 'saleblanket.saleblanket'

    @api.model
    def default_get(self, fields):
        res = super(BlanketOrder, self).default_get(fields)
        expiry_date = self.env['ir.config_parameter'].get_param('equip3_sale_other_operation_cont.bo_expiry_date')
        if expiry_date:
            res['expiry_date'] = datetime.now() + timedelta(days=int(expiry_date))
        return res

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        res = super(BlanketOrder, self).onchange_partner_id()
        product_pricelist_id = self.env.company.product_pricelist_default.id
        if self.partner_id:
            self.report_template_id = self.partner_id.report_sale_template_id.id or False
            if not self.partner_id.property_product_pricelist:
                self.pricelist_id = product_pricelist_id

    def _prepare_invoice(self):
        invoice_vals = super(BlanketOrder, self)._prepare_invoice()
        if invoice_vals:
            invoice_vals.update(
                {'report_template_id': self.partner_invoice_id and self.partner_invoice_id.report_sale_template_id.id or False})
        return invoice_vals

    @api.model
    def _default_report_template(self):
        report_obj = self.env['ir.actions.report']
        report_id = report_obj.search(
            [('model', '=', 'saleblanket.saleblanket'), ('report_name', '=', 'equip3_sale_other_operation_cont.report_blanket_order_custom')])
        if report_id:
            report_id = report_id[0]
        else:
            report_id = report_obj.search([('model', '=', 'saleblanket.saleblanket')])
        return report_id

    @api.depends('partner_id')
    def _default_report_template1(self):
        report_obj = self.env['ir.actions.report']
        report_id = report_obj.search(
            [('model', '=', 'saleblanket.saleblanket'), ('report_name', '=', 'equip3_sale_other_operation_cont.report_blanket_order_custom')])
        if report_id:
            report_id = report_id[0]
        else:
            report_id = report_obj.search([('model', '=', 'saleblanket.saleblanket')])
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
        res = super(BlanketOrder, self).print_quotation()
        if self.report_template_id or self.partner_id and self.partner_id.report_template_id or self.company_id and self.company_id.report_sale_template_id:
            report_id = self.report_template_id or self.partner_id and self.partner_id.report_template_id or self.company_id and self.company_id.report_sale_template_id
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
        blanket_obj = self.env['saleblanket.saleblanket']
        lang = self._context.get("lang")
        lang_obj = self.env['res.lang']
        ids = lang_obj.search([("code", "=", lang or 'en_US')])
        sale = blanket_obj.search([('name', '=', origin)])
        if sale:
            timestamp = datetime.datetime.strptime(
                sale.date_order, tools.DEFAULT_SERVER_DATETIME_FORMAT)
            ts = odoo.fields.Datetime.context_timestamp(self, timestamp)
            n_date = ts.strftime(ids.date_format)
            if sale:
                return n_date
        return False

    def _get_invoice_date(self):
        self.ensure_one()
        res = {}
        blanket_obj = self.env['saleblanket.saleblanket']
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
        blanket_obj = self.env['saleblanket.saleblanket']
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

    def _check_website_quote_installed(self):
        self.ensure_one()
        module_obj = self.env['ir.module.module'].sudo()
        quote_installed = module_obj.search(
            [('name', '=', 'website_quote'), ('state', '=', 'installed')])
        res = {}
        if quote_installed:
            return True
        return False

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

    report_template_id1 = fields.Many2one('ir.actions.report', string="Blanket Order Template1", compute='_default_report_template1',
                                          help="Please select Template report for Blanket Order", domain=[('model', '=', 'saleblanket.saleblanket')])
    report_template_id = fields.Many2one('ir.actions.report', string="Blanket Order Template",
                                         help="Please select Template report for Blanket Order", domain=[('model', '=', 'saleblanket.saleblanket')])
    amount_to_text = fields.Char(compute='_amount_in_words',
                                 string='In Words', help="The amount in words")


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_external_link = fields.Boolean('Is External Link', default=False)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        res = super(ResPartner, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                      submenu=submenu)
        is_external_link = self.env.context.get("default_is_external_link")
        doc = etree.XML(res['arch'])
        if is_external_link and view_type == 'form':
            for node in doc.xpath("//field"):
                modifiers = simplejson.loads(node.get("modifiers"))
                modifiers['readonly'] = True
                node.set('modifiers', simplejson.dumps(modifiers))
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

class ResBranch(models.Model):
    _inherit = 'res.branch'

    is_external_link = fields.Boolean('Is External Link', default=False)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        res = super(ResBranch, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                      submenu=submenu)
        is_external_link = self.env.context.get("default_is_external_link")
        doc = etree.XML(res['arch'])
        if is_external_link and view_type == 'form':
            for node in doc.xpath("//field"):
                modifiers = simplejson.loads(node.get("modifiers"))
                modifiers['readonly'] = True
                node.set('modifiers', simplejson.dumps(modifiers))
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    is_external_link = fields.Boolean('Is External Link', default=False)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        res = super(ProductPricelist, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                      submenu=submenu)
        is_external_link = self.env.context.get("default_is_external_link")
        doc = etree.XML(res['arch'])
        if is_external_link and view_type == 'form':
            for node in doc.xpath("//field"):
                modifiers = simplejson.loads(node.get("modifiers"))
                modifiers['readonly'] = True
                node.set('modifiers', simplejson.dumps(modifiers))
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res