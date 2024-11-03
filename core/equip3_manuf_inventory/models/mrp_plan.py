from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MrpPlan(models.Model):
    _name = 'mrp.plan'
    _inherit = ['mrp.plan', 'mrp.material.request']

    @api.model
    def _default_mrp_allow_submit_it(self):
        return eval(self.env['ir.config_parameter'].sudo().get_param('equip3_manuf_inventory.mrp_allow_submit_it_pp', 'False'))

    @api.model
    def _default_mrp_allow_submit_it_partial(self):
        return eval(self.env['ir.config_parameter'].sudo().get_param('equip3_manuf_inventory.mrp_allow_submit_it_partial_pp', 'False'))

    @api.model
    def _default_mrp_allow_submit_it_partial_not_empty(self):
        return eval(self.env['ir.config_parameter'].sudo().get_param('equip3_manuf_inventory.mrp_allow_submit_it_partial_not_empty_pp', 'False'))

    @api.model
    def _default_mrp_allow_submit_mr(self):
        return eval(self.env['ir.config_parameter'].sudo().get_param('equip3_manuf_inventory.mrp_allow_submit_mr_pp', 'False'))

    @api.model
    def _default_mrp_allow_submit_mr_partial(self):
        return eval(self.env['ir.config_parameter'].sudo().get_param('equip3_manuf_inventory.mrp_allow_submit_mr_partial_pp', 'False'))
    
    can_transfer_finished_goods = fields.Boolean(compute='_compute_can_transfer_finished_goods')
    show_transfer_back_material_button = fields.Boolean(compute='_compute_show_transfer_back_material_button')
    transfer_fn_goods_count = fields.Integer(compute='_compute_transfer_fn_goods_count')

    orderpoint_id = fields.Many2one('stock.warehouse.orderpoint', string='Orderpoint')

    mrp_allow_submit_it = fields.Boolean(string='Allow Submit Transfer Request', default=_default_mrp_allow_submit_it)
    mrp_allow_submit_it_partial = fields.Boolean(string='Allow Submit Partial Internal Transfer', default=_default_mrp_allow_submit_it_partial)
    mrp_allow_submit_it_partial_not_empty = fields.Boolean(string='Allow Submit Partial Internal Transfer Not Empty', default=_default_mrp_allow_submit_it_partial_not_empty)

    mrp_allow_submit_mr = fields.Boolean(string='Allow Submit Material Request', default=_default_mrp_allow_submit_mr)
    mrp_allow_submit_mr_partial = fields.Boolean(string='Allow Submit Partial Material Request', default=_default_mrp_allow_submit_mr_partial)

    def _compute_can_transfer_finished_goods(self):
        for record in self:
            record.can_transfer_finished_goods = any(mo.can_transfer_finished_goods for mo in record.mrp_order_ids)
    
    def _compute_show_transfer_back_material_button(self):
        for record in self:
            record.show_transfer_back_material_button = any(mo.state in ('to_close', 'done', 'cancel') for mo in record.mrp_order_ids)
    
    def _compute_transfer_fn_goods_count(self):
        internal_transfer = self.env['internal.transfer']
        for record in self:
            record.transfer_fn_goods_count = internal_transfer.search_count([
                ('source_document', '=', record.plan_id),
                ('is_mrp_transfer_good', '=', True)
            ])

    def transfer_back_material(self):
        self.ensure_one()
        move_values = [{
            'move_line_sequence': sequence + 1,
            'name': self.name,
            'product_id': move.product_id.id,
            'product_uom_qty': move.product_uom_qty,
            'product_uom': move.product_uom.id,
            'is_adjustable_picking': True
        } for sequence, move in enumerate(self.mrp_order_ids.filtered(
            lambda m: m.state in ('to_close', 'done', 'cancel')).mapped('move_raw_ids'))]

        picking_values = {
            'default_company_id': self.company_id.id,
            'default_branch_id': self.branch_id.id,
            'default_move_ids_without_package': move_values,
            'default_origin': self.name,
            'default_is_readonly_origin': True
        }

        action = self.env['ir.actions.actions']._for_xml_id('stock.action_picking_tree_all')
        context = dict(eval(action.get('context', '').strip() or '{}', self._context), create=False)
        context.update(picking_values)
        action.update({
            'name': _('Transfer Back Material'),
            'context': context,
            'views': [(self.env.ref('stock.view_picking_form').id, 'form')],
            'target': 'new',
        })
        return action

    def action_transfer_fn_goods(self):
        InternalTransfer = self.env['internal.transfer']
        Move = self.env['stock.move']
        Product = self.env['product.product']

        draft_transfers = InternalTransfer.search([
            ('source_document', '=', self.plan_id), 
            ('is_mrp_transfer_good', '=', True),
            ('state', 'in', ('draft', 'to_approve', 'approved'))
        ])

        if draft_transfers:
            raise ValidationError(_('Please confirm previous transfer first!'))

        origin = self.plan_id
        order_ids = self.mrp_order_ids.filtered(lambda o: o.can_transfer_finished_goods)
        stock_move_ids = order_ids.mapped('move_finished_ids').filtered(lambda o: not o.byproduct_id)
        company_id = self.company_id
        branch_id = self.branch_id
        analytic_tag_ids = self.analytic_tag_ids

        now = fields.Datetime.now()

        warehouse_moves = {}
        for move in stock_move_ids:
            warehouse_id = move.location_dest_id.get_warehouse().id
            if warehouse_id in warehouse_moves:
                warehouse_moves[warehouse_id] |= move
            else:
                warehouse_moves[warehouse_id] = move
    
        res_ids = []
        for warehouse_id, moves in warehouse_moves.items():

            groups = self.env['stock.move'].read_group(
                [('id', 'in', moves.ids)], 
                ['product_id', 'product_uom'],
                ['product_id', 'product_uom'],
                lazy=False)

            location_id = moves[0].location_dest_id.id
            move_values = []
            for sequence, group in enumerate(groups):
                group_moves = Move.search(group['__domain'])

                product = Product.browse(group['product_id'][0])
                product_uom_qty = sum([max(0, move.product_uom_qty - move.transfered_good_qty) for move in group_moves])

                if not product_uom_qty:
                    continue
                    
                move_values += [(0, 0, {
                    'sequence': sequence + 1,
                    'source_location_id': location_id,
                    'destination_location_id': location_id,
                    'product_id': product.id,
                    'description': product.display_name,
                    'qty': product_uom_qty,
                    'uom': group['product_uom'][0],
                    'scheduled_date': now,
                    'analytic_account_group_ids': [(6, 0, analytic_tag_ids.ids)],
                    'production_ids': [(4, move.production_id.id) for move in group_moves]
                })]

            values = {
                'requested_by': self.env.user.id,
                'source_warehouse_id': warehouse_id,
                'source_location_id': location_id,
                'destination_warehouse_id': warehouse_id,
                'destination_location_id': location_id,
                'company_id': company_id.id,
                'branch_id': branch_id.id,
                'scheduled_date': now,
                'source_document': origin,
                'product_line_ids': move_values,
                'is_mrp_transfer_good': True,
                'analytic_account_group_ids': [(6, 0, analytic_tag_ids.ids)],
                'is_single_source_location': True,
                'is_single_destination_location': True,
            }
            res = InternalTransfer.create(values)
            res_ids += [res.id]

        action = self.env['ir.actions.actions']._for_xml_id('equip3_inventory_operation.action_internal_transfer_request')
        if len(res_ids) == 1:
            action.update({
                'views':  [(self.env.ref('equip3_manuf_inventory.view_form_internal_transfer_good').id, 'form')], 
                'res_id': res_ids[0],
                'target': 'new',
            })
        else:
            action.update({
                'domain': [('id', 'in', res_ids)],
            })
        
        return action

    def action_view_transfer_fn_goods(self):
        return self.action_view_model(
            'equip3_inventory_operation.action_internal_transfer_request',
            'internal.transfer',
            'equip3_manuf_inventory.view_form_internal_transfer_good',
            [('source_document', '=', self.plan_id), ('is_mrp_transfer_good', '=', True)],
        )

    def _get_material_moves(self):
        orders = self.env.context.get('order_ids')
        if not orders:
            return super(MrpPlan, self)._get_material_moves()
        return self.mo_stock_move_ids.filtered(lambda o: o.raw_material_production_id in orders)

    def action_transfer_request(self):
        if not self.mrp_allow_submit_it_partial or self.env.context.get('skip_wizard', False):
            res = super(MrpPlan, self).action_transfer_request()
            orders = self.env.context.get('order_ids', self.env['mrp.production'])
            if orders.exists():
                orders.write({'is_transfer_requested': True})
            return res
        return {
            'name': _('Internal Transfer'),
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.material.request.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {
                'default_plan_id': self.id,
                'default_action': 'action_transfer_request'
            }
        }

    def action_material_request(self):
        if not self.mrp_allow_submit_mr_partial or self.env.context.get('skip_wizard', False):
            res = super(MrpPlan, self).action_material_request()
            orders = self.env.context.get('order_ids', self.env['mrp.production'])
            if orders.exists():
                orders.write({'is_material_requested': True})
            return res
        return {
            'name': _('Material Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.material.request.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {
                'default_plan_id': self.id,
                'default_action': 'action_material_request'
            }
        }
