# -*- coding: utf-8 -*-
from odoo import models, fields, _


class SaleOrderReportWizard(models.Model):
    _name = 'sale.order.report.wizard'
    _description = "Wizard for sale order report"

    report_type = fields.Selection([('sale_order_print', 'Sale Order Print'),
                                    ('custom_Print', 'Custom Print')], string="Select Report",
                                   default='sale_order_print')

    def action_print(self):
        context = dict(self.env.context) or {}
        sale_order_id = self.env['sale.order'].browse(context.get('active_ids'))
        if self.report_type == 'sale_order_print':
            return self.env.ref('sale.action_report_saleorder').report_action(sale_order_id)
        else:
            return {
                'name': _('Create Sale PrintOut'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'sale.printout.editor',
                'target': 'new',
                "context": context,
            }
