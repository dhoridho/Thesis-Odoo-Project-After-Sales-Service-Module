from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class MrpProductionInherit(models.Model):
    _inherit = 'mrp.production'

    def _get_move_finished_values(self, product_id, product_uom_qty, product_uom, operation_id=False, byproduct_id=False):
        values = super(MrpProductionInherit, self)._get_move_finished_values(product_id, product_uom_qty, product_uom, operation_id, byproduct_id)
        if not byproduct_id:
            values['subcon_is_finished_good'] = True
        return values

    def _compute_subcon_count(self):
        query = """
        SELECT
            po.subcon_production_id AS production_id,
            SUM(CASE WHEN po.state IN ('draft', 'sent') THEN 1 ELSE 0 END) AS pending,
            SUM(CASE WHEN po.state NOT IN ('draft', 'sent') THEN 1 ELSE 0 END) AS not_pending
        FROM
            purchase_order po
        WHERE
            po.is_a_subcontracting IS True AND
            po.subcon_production_id IN %s
        GROUP BY
            po.subcon_production_id
        """
        self.env.cr.execute(query, [tuple(self.ids)])
        purchase = {o[0]: {'pending': o[1], 'not_pending': o[2]} for o in self.env.cr.fetchall()}

        query = """
        SELECT
            pr.subcon_production_id AS production_id,
            COUNT(pr.id)
        FROM
            purchase_request pr
        WHERE
            pr.is_a_subcontracting IS True AND
            pr.purchase_req_state = 'pending' AND
            pr.subcon_production_id IN %s
        GROUP BY
            pr.subcon_production_id
        """
        self.env.cr.execute(query, [tuple(self.ids)])
        request = {o[0]: o[1] for o in self.env.cr.fetchall()}

        query = """
        SELECT
            pr.subcon_production_id AS production_id,
            COUNT(pr.id)
        FROM
            purchase_requisition pr
        WHERE
            pr.subcon_production_id IN %s
        GROUP BY
            pr.subcon_production_id
        """
        self.env.cr.execute(query, [tuple(self.ids)])
        requisition = {o[0]: o[1] for o in self.env.cr.fetchall()}

        for production in self:
            production_id = production.id
            production.subcon_pr_pending_count = request.get(production_id, 0)
            production.subcon_po_pending_count = purchase.get(production_id, {}).get('pending', 0)
            production.subcon_count = purchase.get(production_id, {}).get('not_pending', 0)
            production.subcon_requisition_count = requisition.get(production_id, 0)

    is_subcontracted = fields.Boolean()
    can_be_subcontracted = fields.Boolean(related='bom_id.can_be_subcontracted')
    subcon_pr_pending_count = fields.Integer(compute=_compute_subcon_count)
    subcon_po_pending_count = fields.Integer(compute=_compute_subcon_count)
    subcon_count = fields.Integer(compute=_compute_subcon_count)
    subcon_requisition_count = fields.Integer(compute=_compute_subcon_count)

    def split_workorders(self, purchase):
        self.ensure_one()
        for workorder in self.workorder_ids:
            new_workorder = workorder._split(purchase)

            if not new_workorder:
                continue

            (new_workorder.move_raw_ids | new_workorder.byproduct_ids)._adjust_procure_method()
            (new_workorder.move_raw_ids | new_workorder.byproduct_ids)._action_confirm()

            new_workorder._action_confirm()
            (new_workorder.move_raw_ids | new_workorder.byproduct_ids)._trigger_scheduler()

        return self.workorder_ids

    def action_confirm(self):
        for record in self:
            move_byproduct_ids = record.move_byproduct_ids or record.move_finished_ids.filtered(
                lambda m: m.byproduct_id)
            if sum(move_byproduct_ids.mapped('allocated_cost')) > 100:
                raise UserError(_('Total By-Products Allocated Cost must be less or equal to 100%!'))
        return super(MrpProductionInherit, self).action_confirm()

    def action_subcontracting(self):
        view_id = self.env.ref('equip3_manuf_subcontracting.mrp_subcontracting_wizard_view').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subcontracting'),
            'res_model': 'mrp.subcontracting.wizard',
            'target': 'new',
            'view_mode': 'form',
            'views': [[view_id, 'form']],
            'context': {
                'default_production_id': self.id,
                'default_product_qty': self.product_qty,
            }
        }

    def action_view_pr_subcon_pending(self):
        records = self.env['purchase.request'].search([('subcon_production_id', '=', self.id), ('is_a_subcontracting', '=', True)])
        action = self.env['ir.actions.actions']._for_xml_id('equip3_purchase_operation.product_purchase_requests_services')
        if len(records) <= 1:
            action['view_mode'] = 'form'
            action['views'] = [[False, 'form']]
            action['res_id'] = records.id
        return action

    def action_view_po_subcon_pending(self):
        records = self.env['purchase.order'].search([('subcon_production_id', '=', self.id), ('is_a_subcontracting', '=', True)])
        action = self.env['ir.actions.actions']._for_xml_id('equip3_purchase_operation.product_requests_for_quotation_services')
        if len(records) <= 1:
            action['view_mode'] = 'form'
            action['views'] = [[False, 'form']]
            action['res_id'] = records.id
        return action

    def action_view_purchase_requisition(self):
        return self.action_view_model(
            'equip3_purchase_other_operation.product_purchase_blanket_order_services_orders',
            'purchase.requisition',
            'purchase_requisition.view_purchase_requisition_form',
            [('subcon_production_id', '=', self.id)],
        )
