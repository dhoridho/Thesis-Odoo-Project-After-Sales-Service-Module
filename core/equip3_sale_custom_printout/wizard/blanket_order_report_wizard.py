# -*- coding: utf-8 -*-
from odoo import models, fields


class BlanketOrderReportWizard(models.Model):
    _name = 'saleblanket.order.report.wizard'
    _description = "Wizard for blanket order report"

    report_type = fields.Selection([('blanket_order_print', 'Blanket Order Print'),
                                    ('custom_Print', 'Custom Print')], string="Select Report",
                                   default='blanket_order_print')

    def action_print(self):
        if self.report_type == 'blanket_order_print':
            return self.env.ref('equip3_sale_other_operation_cont.report_sale_blanket').report_action(self)
        else:
            return {
                'name': "Print Custom Report",
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'blanket.printout.editor',
                'target': 'new',
            }


BlanketOrderReportWizard()
