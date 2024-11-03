# -*- coding: utf-8 -*-
# Part of AppJetty. See LICENSE file for full copyright and licensing details.
import odoo
import sys
# from imp import reload
import datetime
from odoo import fields, models, api, tools
from odoo import tools
from odoo.tools.misc import formatLang


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_assign(self):
        result = super(StockPicking, self).action_assign()
        for picking in self:
            picking.write({'report_template_id': picking.partner_id.report_picking_template_id and picking.partner_id.report_picking_template_id.id or picking.partner_id.report_delivery_template_id and picking.partner_id.report_delivery_template_id.id or False})
        return result

    @api.onchange('picking_type_id', 'partner_id')
    def onchange_picking_type(self):
        result = super(StockPicking, self).onchange_picking_type()
        if self.picking_type_id:
            if self and self.partner_id:
                self.report_template_id = self.partner_id.report_picking_template_id and self.partner_id.report_picking_template_id.id or self.partner_id.report_delivery_template_id and self.partner_id.report_delivery_template_id.id or False
        return result

    @api.model
    def _default_stock_report_template(self):
        report_obj = self.env['ir.actions.report']
        report_id = report_obj.search(
            [('model', '=', 'stock.picking'), ('report_name', '=', 'general_template.report_delivery_custom')])
        if report_id:
            report_id = report_id[0]
        else:
            report_id = report_obj.search([('model', '=', 'stock.picking')])[0]
        return report_id

    @api.depends('partner_id')
    def _default_stock_report_template1(self):
        report_obj = self.env['ir.actions.report']
        report_id = report_obj.search(
            [('model', '=', 'stock.picking'), ('report_name', '=', 'general_template.report_delivery_custom')])
        if report_id:
            report_id = report_id[0]
        else:
            report_id = report_obj.search([('model', '=', 'stock.picking')])[0]
        if self.report_template_id and self.report_template_id.id < report_id.id:
            self.write(
                {'report_template_id': report_id and report_id.id or False})
        self.report_template_id = self.report_template_id or self.partner_id and self.partner_id.report_picking_template_id.id or self.partner_id and self.partner_id.report_delivery_template_id.id or False
        self.report_template_id1 = report_id and report_id.id or False

    def do_print_picking(self):
        """ Print the invoice and mark it as sent, so that we can see more
            easily the next step of the workflow
        """
        self.ensure_one()
        self.sent = True
        res = super(StockPicking, self).do_print_picking()
        if self.report_template_id or self.partner_id and self.partner_id.report_template_id or self.company_id and self.company_id.report_template_id:
            report_id = self.report_template_id or self.partner_id and self.partner_id.report_template_id or self.company_id and self.company_id.report_picking_template_id
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
        # sys.setdefaultencoding("utf-8")
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
        # sys.setdefaultencoding("utf-8")
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_origin_date(self, origin):
        self.ensure_one()
        res = {}
        sale_obj = self.env['stock.picking']
        lang = self._context.get("lang")
        lang_obj = self.env['res.lang']
        ids = lang_obj.search([("code", "=", lang or 'en_US')])
        sale = sale_obj.search([('name', '=', origin)])
        if sale:
            timestamp = datetime.datetime.strptime(
                sale.date_order, tools.DEFAULT_SERVER_DATETIME_FORMAT)
            ts = odoo.fields.Datetime.context_timestamp(self, timestamp)
            n_date = ts.strftime(ids.date_format)  # .decode('utf-8')
            if sale:
                return n_date
        return False

    def _get_invoice_date(self):
        self.ensure_one()
        res = {}
        sale_obj = self.env['stock.picking']
        lang = self._context.get("lang")
        lang_obj = self.env['res.lang']
        ids = lang_obj.search([("code", "=", lang or 'en_US')])
        if self.date_invoice:
            timestamp = datetime.datetime.strptime(
                self.date_invoice, tools.DEFAULT_SERVER_DATE_FORMAT)
            ts = odoo.fields.Datetime.context_timestamp(self, timestamp)
            n_date = ts.strftime(ids.date_format)  # .decode('utf-8')
            if self:
                return n_date
        return False

    def _get_invoice_due_date(self):
        self.ensure_one()
        res = {}
        sale_obj = self.env['stock.picking']
        lang = self._context.get("lang")
        lang_obj = self.env['res.lang']
        ids = lang_obj.search([("code", "=", lang or 'en_US')])
        if self.date_due:
            timestamp = datetime.datetime.strptime(
                self.date_due, tools.DEFAULT_SERVER_DATE_FORMAT)
            ts = odoo.fields.Datetime.context_timestamp(self, timestamp)
            n_date = ts.strftime(ids.date_format)  # .decode('utf-8')
            if self:
                return n_date
        return False

    def _get_tax_amount(self, amount):
        self.ensure_one()
        res = {}
        currency = self.currency_id or self.company_id.currency_id
        res = formatLang(self.env, amount, currency_obj=currency)
        return res

    def _check_delivery_installed(self):
        self.ensure_one()
        module_obj = self.env['ir.module.module'].sudo()
        delivery_installed = module_obj.search(
            [('name', '=', 'delivery'), ('state', '=', 'installed')])
        res = {}
        if delivery_installed:
            return True
        return False

    # report_template_id1 = fields.Many2one('ir.actions.report', string="Picking Template1", compute='_default_stock_report_template1',
    #                                       help="Please select Template report for Picking", domain=[('model', '=', 'stock.picking')])
    report_template_id1 = fields.Many2one('ir.actions.report', string="Picking Template1",
                                          help="Please select Template report for Picking", domain=[('model', '=', 'stock.picking')])
    report_template_id = fields.Many2one('ir.actions.report', string="Picking Template",
                                         help="Please select Template report for Picking", domain=[('model', '=', 'stock.picking')])
