# -*- coding: utf-8 -*-
# Part of AppJetty. See LICENSE file for full copyright and licensing details.
import odoo
from odoo import fields, models, api, tools


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _default_report_template(self):
        report_obj = self.env['ir.actions.report']
        report_id = report_obj.search(
            [('model', '=', 'account.move'), ('report_name', '=', 'general_template.report_invoice_template_custom')])
        if report_id:
            report_id = report_id[0]
        else:
            report_id = report_obj.search([('model', '=', 'account.move')])[0]
        return report_id

    def _default_report_template1(self):
        report_obj = self.env['ir.actions.report']
        report_id = report_obj.search(
            [('model', '=', 'account.move'), ('report_name', '=', 'general_template.report_invoice_template_custom')])
        if report_id:
            report_id = report_id[0]
        else:
            report_id = report_obj.search([('model', '=', 'account.move')])[0]
        if self.report_template_id and self.report_template_id.id < report_id.id:
            self.write(
                {'report_template_id': report_id and report_id.id or False})
            #self.report_template_id = report_id and report_id.id or False
        self.report_template_id1 = report_id and report_id.id or False

    @api.model
    def _default_report_po_template(self):
        report_obj = self.env['ir.actions.report']
        report_id = report_obj.search(
            [('model', '=', 'purchase.order'), ('report_name', '=', 'general_template.report_purchase_custom')])
        if report_id:
            report_id = report_id[0]
        else:
            report_id = report_obj.search(
                [('model', '=', 'purchase.order')])[0]
        return report_id

    def _default_report_po_template1(self):
        report_obj = self.env['ir.actions.report']
        report_id = report_obj.search(
            [('model', '=', 'purchase.order'), ('report_name', '=', 'general_template.report_purchase_custom')])
        if report_id:
            report_id = report_id[0]
        else:
            report_id = report_obj.search(
                [('model', '=', 'purchase.order')])[0]
        if self.report_po_template_id and self.report_po_template_id.id < report_id.id:
            self.write(
                {'report_po_template_id': report_id and report_id.id or False})
        self.report_po_template_id1 = report_id and report_id.id or False

    @api.model
    def _default_report_delivery_template(self):
        report_obj = self.env['ir.actions.report']
        report_id = report_obj.search(
            [('model', '=', 'stock.picking'), ('report_name', '=', 'general_template.report_delivery_custom')])
        if report_id:
            report_id = report_id[0]
        else:
            report_id = report_obj.search([('model', '=', 'stock.picking')])[0]
        return report_id

    def _default_report_delivery_template1(self):
        report_obj = self.env['ir.actions.report']
        report_id = report_obj.search(
            [('model', '=', 'stock.picking'), ('report_name', '=', 'general_template.report_delivery_custom')])
        if report_id:
            report_id = report_id[0]
        else:
            report_id = report_obj.search([('model', '=', 'stock.picking')])[0]
        if self.report_delivery_template_id and self.report_delivery_template_id.id < report_id.id:
            self.write(
                {'report_delivery_template_id': report_id and report_id.id or False})
        self.report_delivery_template_id1 = report_id and report_id.id or False

    @api.model
    def _default_report_sale_template(self):
        report_obj = self.env['ir.actions.report']
        report_id = report_obj.search(
            [('model', '=', 'sale.order'), ('report_name', '=', 'general_template.report_sale_order_custom')])
        if report_id:
            report_id = report_id[0]
        else:
            report_id = report_obj.search([('model', '=', 'sale.order')])[0]
        return report_id

    def _default_report_sale_template1(self):
        report_obj = self.env['ir.actions.report']
        report_id = report_obj.search(
            [('model', '=', 'sale.order'), ('report_name', '=', 'general_template.report_sale_order_custom')])
        if report_id:
            report_id = report_id[0]
        else:
            report_id = report_obj.search([('model', '=', 'sale.order')])[0]
        if self.report_sale_template_id and self.report_sale_template_id.id < report_id.id:
            self.write(
                {'report_sale_template_id': report_id and report_id.id or False})
        self.report_sale_template_id1 = report_id and report_id.id or False

    report_template_id1 = fields.Many2one('ir.actions.report', string="Invoice Template1", compute='_default_report_template1',
                                          help="Please select Template report for Invoice", domain=[('model', '=', 'account.move')])
    report_template_id = fields.Many2one('ir.actions.report', string="Invoice Template",
                                         help="Please select Template report for Invoice", domain=[('model', '=', 'account.move')])
    report_sale_template_id1 = fields.Many2one('ir.actions.report', string="Sale Order Template1", compute='_default_report_sale_template1',
                                               help="Please select Template report for Sale Order", domain=[('model', '=', 'sale.order')])
    report_sale_template_id = fields.Many2one('ir.actions.report', string="Sale Order Template",
                                              help="Please select Template report for Sale Order", domain=[('model', '=', 'sale.order')])
    report_po_template_id1 = fields.Many2one('ir.actions.report', string="Purchase Order Template1", compute='_default_report_po_template1',
                                             help="Please select Template report for Purchase Order", domain=[('model', '=', 'purchase.order')])
    report_po_template_id = fields.Many2one('ir.actions.report', string="Purchase Order Template",
                                            help="Please select Template report for Purchase Order", domain=[('model', '=', 'purchase.order')])
    report_rfq_template_id = fields.Many2one('ir.actions.report', string="RFQ Template",
                                             help="Please select Template report for RFQ", domain=[('model', '=', 'purchase.order')])
    report_delivery_template_id1 = fields.Many2one('ir.actions.report', string="Delivery Note Template1", compute='_default_report_delivery_template1',
                                                   help="Please select Template report for Delivery Note ", domain=[('model', '=', 'stock.picking')])
    report_delivery_template_id = fields.Many2one('ir.actions.report', string="Delivery Note Template",
                                                  help="Please select Template report for Delivery Note ", domain=[('model', '=', 'stock.picking')])
    report_picking_template_id = fields.Many2one('ir.actions.report', string="Picking List Template",
                                                 help="Please select Template report for Picking List", domain=[('model', '=', 'stock.picking')])
