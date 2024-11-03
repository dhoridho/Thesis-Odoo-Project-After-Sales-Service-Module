from odoo import _, api, fields, models


class ProcurementRfqWizard(models.TransientModel):
    _name = 'procurement.rfq.wizard'

    def _get_partner_domain(self):
        return [('company_id', '=', self.env.company.id), ('vendor_sequence', '!=', False)]

    partner_id = fields.Many2one(
        comodel_name='res.partner', string='Vendor', required=True, domain=_get_partner_domain)
    procurement_rfq_line = fields.Many2one(
        comodel_name='procurement.rfq.line', string='Procurement RFQ Line')

    def action_confirm(self):
        self.ensure_one()
        context = dict(self.env.context) or {}
        if context.get('active_model') == 'procurement.planning.model':
            procurement_plan_id = self.env['procurement.planning.model'].browse(
                context.get('active_id'))

            order_line = [(0, 0, {
                'product_id': line.product_id.id,
                'product_template_id': line.product_id.product_tmpl_id.id,
                'name': line.product_id.name,
                'date_planned': fields.Datetime.now(),
                'product_qty': line.request_to_order - line.quantity_ordered,
                'product_uom': line.uom_id.id})for line in procurement_plan_id.procurement_line if line.request_to_order > 0]
            analytic_group_ids = procurement_plan_id.analytic_group_ids.ids
            ctx = {
                'quotation_only': True,
                'goods_order': 1,
            }
            rfq_vals = {
                'procurement_planning_id': procurement_plan_id.id,
                'branch_id': procurement_plan_id.branch_id.id,
                'partner_id': self.partner_id.id,
                'is_goods_orders': True,
                'is_delivery_receipt': True,
                'is_single_delivery_destination': True,
                'date_order': fields.Datetime.now(),
                'date_planned': fields.Datetime.now(),
                'destination_warehouse_id': procurement_plan_id.warehouse_id.id,
                'analytic_account_group_ids': [(6, 0, analytic_group_ids)],
                'order_line': order_line,
            }

            rfq = self.env['purchase.order'].with_context(ctx).create(rfq_vals)
            rfq._onchange_destination_warehouse()

            return {
                'name': _("RFQ"),
                'view_mode': 'form',
                'view_id': self.env.ref('equip3_inventory_purchase_operation.purchase_order_inventory_control').id,
                'res_model': 'purchase.order',
                'type': 'ir.actions.act_window',
                'res_id': rfq.id,
                'target': 'current',
            }


class ProcurementRfqLine(models.TransientModel):
    _name = 'procurement.rfq.line'

    wiz_id = fields.Many2one(comodel_name='procurement.rfq.wizard')
    product_id = fields.Many2one(
        comodel_name='product.product', string='Product')
    description = fields.Char(string='Description')
    remaining_qty = fields.Float(string='Remaining Quantity')
    qty_to_purchase = fields.Float(string='Quantity to Purchase')
    uom_id = fields.Many2one(comodel_name='uom.uom', string='UoM')
