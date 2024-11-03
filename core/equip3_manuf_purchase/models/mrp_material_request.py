from odoo import models, fields


class MrpMaterialRequest(models.AbstractModel):
    _inherit = 'mrp.material.request'

    def _compute_material_tab_technical_fields(self):
        super(MrpMaterialRequest, self)._compute_material_tab_technical_fields()
        purchase_request = self.env['purchase.request']
        for record in self:
            name = record._get_origin_moves()
            purchase_request_count = purchase_request.search_count([('origin', '=', name)])
            record.write({
                'purchase_request_count': purchase_request_count,
            })

    purchase_request_count = fields.Integer(compute=_compute_material_tab_technical_fields)

    def action_purchase_request(self):
        PurchaseRequest = self.env['purchase.request']
        origin = self._get_origin_moves()

        res_ids = PurchaseRequest.search([
            ('origin', '=', origin),
            ('state', '=', 'draft')
        ]).ids

        if not res_ids:
            Move = self.env['stock.move']
            Product = self.env['product.product']
            UoM = self.env['uom.uom']
            Warehouse = self.env['stock.warehouse']

            
            material_moves = self._get_material_moves()
            company_id = self._get_company()
            branch_id = self._get_branch()
            analytic_tag_ids = self._get_analytic_tags()

            now = fields.Datetime.now()
            stock_move_ids = material_moves.filtered(lambda m: m.product_uom_qty - (m.availability_uom_qty + m.reserved_availability) > 0.0 \
                and m.product_id not in m.raw_material_production_id.child_ids.mapped('product_id'))

            warehouse_moves = {}
            for move in stock_move_ids:
                warehouse_id = move.location_id.get_warehouse().id
                location_id = move.location_id.id
                if (location_id, warehouse_id) in warehouse_moves:
                    warehouse_moves[(location_id, warehouse_id)] |= move
                else:
                    warehouse_moves[(location_id, warehouse_id)] = move

            res_ids = []
            for (location_id, warehouse_id), moves in warehouse_moves.items():
                warehouse = Warehouse.browse(warehouse_id)
                picking_type = self.env['stock.picking.type'].search([('default_location_dest_id', '=', location_id)], limit=1)

                groups = self.env['stock.move'].read_group(
                    [('id', 'in', moves.ids)], 
                    ['product_id', 'product_uom'],
                    ['product_id', 'product_uom'],
                    lazy=False)

                move_values = []
                for sequence, group in enumerate(groups):
                    group_moves = Move.search(group['__domain'])

                    product = Product.browse(group['product_id'][0])

                    product_uom_qty = sum(move.product_uom_qty for move in group_moves) - \
                        (group_moves[0].availability_uom_qty + group_moves[0].reserved_availability)
                        
                    move_values += [(0, 0, {
                        'sequence2': sequence + 1,
                        'name': product.display_name,
                        'product_id': product.id,
                        'product_uom_id': group['product_uom'][0],
                        'product_qty': product_uom_qty,
                        'date_required': fields.Date.today(),
                        'dest_loc_id': warehouse_id,
                        'analytic_account_group_ids': [(6, 0, analytic_tag_ids.ids)],
                        'mrp_force_location_dest_id': location_id
                    })]
                
                values = {
                    'picking_type_id': picking_type.id,
                    'company_id': company_id.id,
                    'branch_id': branch_id.id,
                    'line_ids': move_values,
                    'origin': origin,
                    'destination_warehouse': warehouse_id,
                    'request_date': now,
                    'is_readonly_origin': True,
                    'is_goods_orders': True,
                    'is_single_request_date': True,
                    'is_single_delivery_destination': True,
                    'analytic_account_group_ids': [(6, 0, analytic_tag_ids.ids)]
                }
                res_ids += [PurchaseRequest.create(values).id]

        action = self.env['ir.actions.actions']._for_xml_id('purchase_request.purchase_request_form_action')
        if len(res_ids) == 1:
            action.update({
                'views':  [(self.env.ref('purchase_request.view_purchase_request_form').id, 'form')], 
                'res_id': res_ids[0],
                'target': 'new',
            })
        else:
            action.update({
                'domain': [('id', 'in', res_ids)],
            })
        
        return action

    def action_view_purchase_request(self):
        return self.action_view_model(
            'purchase_request.purchase_request_form_action',
            'purchase.request',
            'purchase_request.view_purchase_request_form',
            [('origin', '=', self._get_origin_moves())],
        )
