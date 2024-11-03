from email.policy import default
from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError , ValidationError
from odoo import tools


class RFQVariableLine(models.Model):
    _inherit = 'rfq.variable.line'

    saving_cost = fields.Float('Cost Saving',compute='compute_cost_saving')
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed'),('cancelled','Cancelled')], 'State', default='draft')
    feedback = fields.Char('Feedback')

    def compute_cost_saving(self):
        for rec in self:
            rec.saving_cost = rec.budget_amount - rec.total

    def send_confirm_msg(self):
        self.state = 'confirmed'
        return True


class PurchaseAgreement(models.Model):
    _inherit = 'purchase.agreement'

    set_single_delivery_destination = fields.Boolean("Single Delivery Destination", default=True)
    destination_warehouse_id = fields.Many2one('stock.warehouse', string="Destination", domain="[('company_id', '=', company_id)]", compute="destination_warehouse_comute")
    analytic_account_group_ids = fields.Many2many('account.analytic.tag', string="Analytic Account Group")

    def destination_warehouse_comute(self):
        stock_warehouse = self.env['stock.warehouse'].search([], order="id", limit=1)
        self.destination_warehouse_id = stock_warehouse[0]

    def _set_expiry_date(self):
        date2= datetime.now()
        for rec in self:
            if rec.is_assets_orders:
                date = rec.date_order_assets
            elif rec.is_services_orders:
                rfq_exp_date_services = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.rfq_exp_date_services')
                date= date2 + timedelta(days=int(rfq_exp_date_services))
            else:
                rfq_exp_date_goods = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.rfq_exp_date_goods')
                date = date2 + timedelta(days=int(rfq_exp_date_goods))
        return date

    def action_analyze_rfq(self):
        if self.is_subcontracting:
            list_id = self.env.ref(
                'equip3_construction_purchase_operation.rfq_variable_line_tree_view').id

            return {
                'name': _('Tender Lines'),
                'type': 'ir.actions.act_window',
                'res_model': 'rfq.variable.line',
                'view_type': 'form',
                'view_mode': 'tree',
                'views': [(list_id, 'tree')],
                'domain': [('state', 'not in', ['cancelled']),
                           ('variable_id.is_subcontracting', '=', True), ('purchase_agreement', '=', self.id)],
                'context': {'search_default_groupby_variable': 1},
                'target': 'current'
            }

        else:
            list_id = self.env.ref(
                'sh_po_tender_management.sh_bidline_tree_view').id
            form_id = self.env.ref(
                'sh_po_tender_management.sh_bidline_form_view').id
            pivot_id = self.env.ref(
                'sh_po_tender_management.purchase_order_line_pivot_custom').id
            return {
                'name': _('Tender Lines'),
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.order.line',
                'view_type': 'form',
                'view_mode': 'tree,pivot,form',
                'views': [(list_id, 'tree'), (pivot_id, 'pivot'), (form_id, 'form')],
                'domain': [('agreement_id', '=', self.id), ('state', 'not in', ['cancel']),
                           ('order_id.selected_order', '=', False)],
                'context': {'search_default_groupby_product': 1},
                'target': 'current'
            }

    def action_view_order(self):
        tree_view_ref = self.env.ref('equip3_construction_purchase_operation.purchase_order_kpis_tree_cons_inherit', False)
        form_view_ref = self.env.ref('equip3_construction_purchase_operation.direct_purchase_form_view_equip3_purchase_other_operation_const_rfq_1', False)
        return {
            'name': _('Selected Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_id': self.id,
            'domain': [('agreement_id', '=', self.id), ('state', 'in', ['purchase'])],
            'target': 'current',
            'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
        }

    def action_view_quote(self):
        tree_view_ref = self.env.ref('equip3_construction_purchase_operation.purchase_order_kpis_tree_cons_inherit', False)
        form_view_ref = self.env.ref('equip3_construction_purchase_operation.direct_purchase_form_view_equip3_purchase_other_operation_const_rfq_1', False)
        return {
            'name': _('Received Quotations'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_id': self.id,
            'domain': [('agreement_id', '=', self.id), ('selected_order', '=', False), ('state', 'in', ['draft'])],
            'target': 'current',
            'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
        }


