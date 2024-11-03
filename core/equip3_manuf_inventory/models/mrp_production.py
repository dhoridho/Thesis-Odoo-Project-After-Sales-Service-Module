from odoo import models, fields, api, _
from odoo.addons.base.models.ir_model import quote
from odoo.exceptions import ValidationError


class MrpProduction(models.Model):
    _name = 'mrp.production'
    _inherit = ['mrp.production', 'mrp.material.request']

    @api.model
    def _default_mrp_allow_submit_it(self):
        return eval(self.env['ir.config_parameter'].sudo().get_param('equip3_manuf_inventory.mrp_allow_submit_it_po', 'False'))

    @api.model
    def _default_mrp_allow_submit_mr(self):
        return eval(self.env['ir.config_parameter'].sudo().get_param('equip3_manuf_inventory.mrp_allow_submit_mr_po', 'False'))

    can_transfer_finished_goods = fields.Boolean(compute='_compute_can_transfer_finished_goods')
    transfer_good_count = fields.Integer(compute='_compute_transfer_good_count')
    any_moves_to_transfer = fields.Boolean(compute='_compute_any_moves_to_transfer')
    transfer_back_count = fields.Integer(compute='_compute_transfer_back_count')

    orderpoint_id = fields.Many2one('stock.warehouse.orderpoint', string='Orderpoint')

    is_transfer_requested = fields.Boolean()
    is_material_requested = fields.Boolean()

    mrp_allow_submit_it = fields.Boolean(string='Allow Submit Material Request', default=_default_mrp_allow_submit_it)
    mrp_allow_submit_mr = fields.Boolean(string='Allow Submit Material Request', default=_default_mrp_allow_submit_mr)

    def _compute_any_moves_to_transfer(self):
        for production in self:
            production.any_moves_to_transfer = production.state == 'done' and \
                any(m.state == 'cancel' and not m.is_transfered for m in production.move_raw_ids)

    def _compute_transfer_back_count(self):
        query = """
        SELECT
            it.source_document AS name,
            COUNT(it.source_document) AS count
        FROM
            internal_transfer it
        WHERE
            it.is_mrp_transfer_back IS True AND
            it.source_document IN ({production_names})
        GROUP BY
            it.source_document
        """.format(production_names=', '.join("'%s'" % name for name in self.mapped('name')))

        self.env.cr.execute(query)
        result = {o['name']: o['count'] for o in self.env.cr.dictfetchall()}

        for production in self:
            production.transfer_back_count = result.get(production.name, 0)

    def _get_transfer_good_domain(self):
        self.ensure_one()
        if self.mrp_plan_id:
            origin = self.mrp_plan_id.plan_id
        else:
            origin = self.name
        return [('is_mrp_transfer_good', '=', True), ('source_document', '=', origin)]

    def _compute_can_transfer_finished_goods(self):
        for record in self:
            finished_moves = record.move_finished_only_ids.filtered(lambda o: o.state == 'done')
            to_transfer_qty = sum(max(0, move.product_uom_qty - move.transfered_good_qty) for move in finished_moves)
            record.can_transfer_finished_goods = to_transfer_qty > 0.0

    def _compute_transfer_good_count(self):
        production_origins = [o.mrp_plan_id.plan_id or o.name for o in self]

        query = """
        SELECT
            it.source_document AS name,
            COUNT(it.source_document) AS count
        FROM
            internal_transfer it
        WHERE
            it.is_mrp_transfer_good IS True AND
            it.source_document IN ({origins})
        GROUP BY
            it.source_document
        """.format(origins=', '.join("'%s'" % name for name in production_origins))

        self.env.cr.execute(query)
        result = {o['name']: o['count'] for o in self.env.cr.dictfetchall()}
        
        for record in self:
            record.transfer_good_count = result.get(record.mrp_plan_id.plan_id or record.name, 0)

    def action_view_internal_transfer(self, res_ids):
        return self.action_view_model(
            'equip3_inventory_operation.action_internal_transfer_request',
            'internal.transfer',
            'equip3_manuf_inventory.view_form_internal_transfer_good',
            [('id', 'in', res_ids)],
        )

    def action_transfer_finished_goods(self):
        InternalTransfer = self.env['internal.transfer']
        Move = self.env['stock.move']
        Product = self.env['product.product']

        draft_transfers = InternalTransfer.search([
            ('source_document', '=', self.name), 
            ('is_mrp_transfer_good', '=', True),
            ('state', 'in', ('draft', 'to_approve', 'approved'))
        ])

        if draft_transfers:
            raise ValidationError(_('Please confirm previous transfer first!'))
        
        origin = self.name
        stock_move_ids = self.move_finished_only_ids
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

                if product_uom_qty <= 0.0:
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

        action = self.action_view_internal_transfer(res_ids)
        action['target'] = 'new'
        return action

    def action_view_transfer_good(self, transfer_ids=None):
        transfers = self.env['internal.transfer'].search(self._get_transfer_good_domain())
        transfer_ids = transfers.filtered(lambda o: any(self in line.production_ids for line in o.product_line_ids)).ids
        return self.action_view_internal_transfer(transfer_ids)

    def transfer_back_material(self):
        self.ensure_one()
        moves_to_transfer = self.move_raw_ids.filtered(lambda m: m.state == 'cancel' and not m.is_transfered)
        transfer = self.env['internal.transfer']
        now = fields.Datetime.now()

        transfers = self.env['internal.transfer']
        for location in set(moves_to_transfer.mapped('location_id')):
            transfers |= transfer.create({
                'source_warehouse_id': location.get_warehouse().id,
                'destination_warehouse_id': location.get_warehouse().id,
                'source_location_id': location.id,
                'destination_location_id': location.id,
                'company_id': self.company_id.id,
                'branch_id': self.branch_id.id,
                'scheduled_date': now,
                'source_document': self.name,
                'is_mrp_transfer_back': True,
                'product_line_ids': [(0, 0, {
                    'sequence': sequence + 1,
                    'product_id': move.product_id.id,
                    'description': move.product_id.display_name,
                    'qty': move.product_uom_qty,
                    'uom': move.product_uom.id,
                    'source_location_id': location.id,
                    'destination_location_id': location.id,
                    'scheduled_date': now
                }) for sequence, move in enumerate(moves_to_transfer.filtered(lambda m: m.location_id == location))]
            })
        moves_to_transfer.write({'is_transfered': True})
        action = self.action_view_internal_transfer(transfres.ids)
        action['target'] = 'new'
        return action

    def action_view_transfer_back(self, transfers=None, target='current'):
        transfers = self.env['internal.transfer'].search([('source_document', '=', self.name), ('is_mrp_transfer_back', '=', True)])
        return self.action_view_internal_transfer(transfers.ids)

    def _get_move_finished_values(self, product_id, product_uom_qty, product_uom, operation_id=False, byproduct_id=False):
        res = super(MrpProduction, self)._get_move_finished_values(product_id, product_uom_qty, product_uom, operation_id, byproduct_id)
        orderpoint = self.orderpoint_id
        if orderpoint:
            res['location_dest_id'] = orderpoint.location_id.id or orderpoint.warehouse_id.lot_stock_id.id
        return res

    @api.onchange('location_dest_id', 'move_finished_ids', 'bom_id', 'orderpoint_id')
    def _onchange_location_dest(self):
        orderpoint = self.orderpoint_id
        if not orderpoint:
            return super(MrpProduction, self)._onchange_location_dest()

        location_dest = orderpoint.location_id or orderpoint.warehouse_id.lot_stock_id
        update_value_list = []
        for move in self.move_finished_ids.filtered(lambda m: not m.byproduct_id):
            update_value_list += [(1, move.id, ({
                'warehouse_id': location_dest.get_warehouse().id,
                'location_dest_id': location_dest.id,
            }))]
        self.move_finished_ids = update_value_list
