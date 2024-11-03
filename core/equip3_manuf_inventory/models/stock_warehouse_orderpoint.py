from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    action_to_take = fields.Selection(selection_add=[
        ('create_mo', 'Create Production Order'),
        ('create_mp', 'Create Production Plan')
    ])

    def _create_production_plan(self, raise_error=True):
        for record in self:
            company = record.company_id
            branch = record.branch_id
            product = record.product_id

            bom = self.env['mrp.bom'].with_context(
                equip_bom_type='mrp',
                branch_id=branch.id
            )._bom_find(product=product, company_id=company.id, bom_type='normal')

            if not bom:
                message = _("Product %s doesn't have any Bill of Material" % product.display_name)
                if not raise_error:
                    _logger.error(message)
                    continue
                raise ValidationError(message)

            matrix_id = False
            if company.manufacturing_plan_conf:
                matrix_id = self.env['mrp.plan']._default_approval_matrix(company=company, branch=branch)

            product_qty = record.qty_to_order
            uom = record.product_uom

            plan = self.env['mrp.plan'].create({
                'name': 'Replenish (%s)' % (record.name,),
                'branch_id': branch.id,
                'company_id': company.id,
                'orderpoint_id': record.id,
                'approval_matrix_id': matrix_id
            })

            wizard = self.env['mrp.production.wizard'].with_context(
                active_model='mrp.plan',
                active_id=plan.id,
                active_ids=plan.ids,
            ).create({
                'plan_id': plan.id,
                'line_ids': [(0, 0, {
                    'product_id': product.id,
                    'product_uom': uom.id,
                    'product_qty': product_qty,
                    'no_of_mrp': 1,
                    'company': company.id,
                    'branch_id': branch.id,
                    'bom_id': bom.id
                })]
            })
            wizard.confirm()

    def _create_production_order(self, raise_error=True):
        user = self.env.user
        for record in self:
            company = record.company_id
            branch = record.branch_id
            product = record.product_id

            bom = self.env['mrp.bom'].with_context(
                equip_bom_type='mrp',
                branch_id=branch.id
            )._bom_find(product=product, company_id=company.id, bom_type='normal')

            if not bom:
                message = _("Product %s doesn't have any Bill of Material" % product.display_name)
                if not raise_error:
                    _logger.error(message)
                    continue
                raise ValidationError(message)

            matrix_id = False
            if company.manufacturing_order_conf:
                matrix_id = self.env['mrp.production']._default_approval_matrix(company=company, branch=branch)

            product_qty = record.qty_to_order
            uom = record.product_uom

            order_values = {
                'bom_id': bom.id,
                'product_id': product.id,
                'product_qty': product_qty,
                'product_uom_id': uom.id,
                'company_id': company.id,
                'branch_id': branch.id,
                'user_id': user.id,
                'orderpoint_id': record.id,
                'approval_matrix_id': matrix_id,
            }

            order = self.env['mrp.production'].create(order_values).sudo()
            order.onchange_product_id()
            order.onchange_branch()
            order._onchange_workorder_ids()
            order._onchange_move_raw()
            order._onchange_move_finished()
            order.onchange_workorder_ids()
            order._onchange_location_dest()


    @api.model
    def action_replenish_orderpoint(self, active_ids=None):
        # TODO: records should be accessed via `self` 
        if not active_ids:
            active_ids = self.ids
        res = super(StockWarehouseOrderpoint, self).action_replenish_orderpoint(active_ids)
        records = self.browse(active_ids)

        orderpoints_plan = records.filtered(lambda o: o.action_to_take == 'create_mp')
        orderpoints_order = records.filtered(lambda o: o.action_to_take == 'create_mo')

        if orderpoints_plan:
            orderpoints_plan._create_production_plan()

        if orderpoints_order:
            orderpoints_order._create_production_order()

        return res

    @api.model
    def _cron_replenish_orderpoint(self):
        records = self.env['stock.warehouse.orderpoint'].search([
            ('auto_trigger_replenishment', '=', True),
            ('qty_to_order', '>', 0.0)
        ])

        orderpoints_plan = records.filtered(lambda o: o.action_to_take == 'create_mp')
        orderpoints_order = records.filtered(lambda o: o.action_to_take == 'create_mo')

        if orderpoints_plan:
            orderpoints_plan._create_production_plan(raise_error=False)

        if orderpoints_order:
            orderpoints_order._create_production_order(raise_error=False)

        return super(StockWarehouseOrderpoint, self)._cron_replenish_orderpoint()
