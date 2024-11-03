
from odoo.exceptions import ValidationError
from odoo import fields, models, api, _


class PrintPurchaseReport(models.TransientModel):
    _name = 'print.purchase.report'

    select_report = fields.Selection([
        ('rfq', 'Request for Quotation Print'),
        ('purchase_order', 'Purchase Order Print'),
        ('custom_print', 'Custom Print'),
    ], default='rfq')
    select_report_rfq = fields.Selection([
        ('rfq', 'Request for Quotation Print'),
        ('custom_print', 'Custom Print'),
    ], default='rfq')
    select_report_po = fields.Selection([
        ('purchase_order', 'Purchase Order Print'),
        ('custom_print', 'Custom Print'),
    ], default='purchase_order')
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase')
    state = fields.Selection(related='purchase_order_id.state')

    @api.onchange('select_report_rfq')
    def _onchange_select_report_rfq(self):
        self.select_report = self.select_report_rfq

    @api.onchange('select_report_po')
    def _onchange_select_report_po(self):
        self.select_report = self.select_report_po

    def action_print(self):
        self.ensure_one()
        if self.select_report in ("rfq","purchase_order"):
            if self.state not in ("purchase","done"):
                return self.env.ref('purchase.report_purchase_quotation').report_action(self.purchase_order_id)
            else:
                return self.env.ref('purchase.action_report_purchase_order').report_action(self.purchase_order_id)
        else:
            return {
                "name": "Custom Print",
                'type': 'ir.actions.act_window',
                'res_model': 'printout.editor',
                'view_mode': 'form',
                'view_type': 'form',
                'views': [[False, 'form']],
                'target': 'new',
                'context': {'active_ids': self.purchase_order_id.ids}
            }
