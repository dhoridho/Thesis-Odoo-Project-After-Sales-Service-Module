from odoo import models, fields, api, _
from datetime import date
from odoo.exceptions import ValidationError
from collections import defaultdict
import json


class MRPMaterialRequest(models.AbstractModel):
    _name = 'mrp.material.request'
    _description = 'MRP Material Request'
    
    def _get_origin_moves(self):
        self.ensure_one()
        if self._name == 'mrp.plan':
            return self.plan_id
        elif self._name == 'mrp.workorder':
            return self.workorder_id
        if 'name' in self.env[self._name]._fields:
            return self.name
        return ''
    
    def _get_material_moves(self):
        self.ensure_one()
        if self._name == 'mrp.plan':
            return self.mo_stock_move_ids
        elif 'move_raw_ids' in self.env[self._name]._fields:
            return self.move_raw_ids
        return self.env['stock.move']

    def _get_location_moves(self):
        self.ensure_one()
        if self._name == 'mrp.plan':
            if self.mrp_order_ids:
                return self.mrp_order_ids[0].location_dest_id
            location_dest_id = self.env['mrp.production']._get_default_location_dest_id()
            return self.env['stock.location'].browse(location_dest_id)
        elif self._name == 'mrp.production':
            return self.location_dest_id
        elif self._name == 'mrp.workorder':
            return self.production_id.location_dest_id
        return self.env['stock.location']
    
    def _get_hide_change_component_btn(self):
        self.ensure_one()
        if self._name in ('mrp.plan', 'mrp.production'):
            return any(wo.state in ['progress', 'done'] for wo in self.workorder_ids)
        return True

    def _get_branch(self):
        if self._name in ('mrp.plan', 'mrp.production', 'mrp.workorder'):
            return self.branch_id
        return self.env['res.branch']

    def _get_company(self):
        if self._name in ('mrp.plan', 'mrp.production', 'mrp.workorder'):
            return self.company_id
        return self.env['res.company']

    def _get_analytic_tags(self):
        if self._name in ('mrp.plan', 'mrp.production'):
            return self.analytic_tag_ids
        elif self._name == 'mrp.workorder':
            return self.analytic_group
        return self.env['account.analytic.tag']

    def _compute_material_tab_technical_fields(self):
        material_request = self.env['material.request']
        internal_transfer = self.env['internal.transfer']
        for record in self:
            name = record._get_origin_moves()
            material_request_count = material_request.search_count([('source_document', '=', name)])
            transfer_request_count = internal_transfer.search_count([('source_document', '=', name), ('is_mrp_transfer_request', '=', True)])
            hide_change_component_btn = record._get_hide_change_component_btn()
            record.write({
                'material_request_count': material_request_count,
                'transfer_request_count': transfer_request_count,
                'hide_change_component_btn': hide_change_component_btn
            })

    material_request_count = fields.Integer(compute=_compute_material_tab_technical_fields)
    transfer_request_count = fields.Integer(compute=_compute_material_tab_technical_fields)
    hide_change_component_btn = fields.Boolean(compute=_compute_material_tab_technical_fields)

    def action_transfer_request(self):
        InternalTransfer = self.env['internal.transfer']
        force_create = self.env.context.get('force_create', False)
        
        origin = self._get_origin_moves()

        transfers = InternalTransfer.search([
            ('is_mrp_transfer_request', '=', True), 
            ('source_document', '=', origin),
        ])

        if force_create and any(transfer.state != 'done' for transfer in transfers):
            raise ValidationError(_('Please done previous internal transfer first!'))

        res_ids = transfers.ids

        if not res_ids or force_create:
            Move = self.env['stock.move']
            Product = self.env['product.product']
            UoM = self.env['uom.uom']
            PickingType = self.env['stock.picking.type']
            Quant = self.env['stock.quant']

            try:
                allow_empty = not self.mrp_allow_submit_it_partial_not_empty
            except AttributeError:
                allow_empty = True

            material_moves = self._get_material_moves()
            company_id = self._get_company()
            branch_id = self._get_branch()
            analytic_tag_ids = self._get_analytic_tags()

            now = fields.Datetime.now()
            stock_move_ids = material_moves.filtered(lambda o: o.product_id not in o.raw_material_production_id.child_ids.mapped('product_id'))

            if allow_empty:
                stock_move_ids = stock_move_ids.filtered(lambda o: o.product_uom_qty - (o.availability_uom_qty + o.reserved_availability) > 0.0)

            product_dest_location_group = defaultdict(lambda: {'reserved': 0.0, 'to_reserve': 0.0})
            for move in stock_move_ids:
                reserved_uom_qty = move.reserved_availability
                to_reserve_uom_qty = move.product_uom_qty - reserved_uom_qty
                product_dest_location_group[(move.product_id, move.location_id)]['reserved'] += move.product_uom._compute_quantity(reserved_uom_qty, move.product_id.uom_id)
                product_dest_location_group[(move.product_id, move.location_id)]['to_reserve'] += move.product_uom._compute_quantity(to_reserve_uom_qty, move.product_id.uom_id)

            not_available_qtys = defaultdict(lambda: {
                'product_qty': 0.0,
                'reserved': 0.0,
                'available': 0.0,
                'other_locations': []
            })
            line_values = []
            for (product, dest_location), qtys in product_dest_location_group.items():
                reserved_qty = qtys['reserved']
                to_reserve_qty = qtys['to_reserve']

                if not allow_empty:
                    quants = Quant.search([
                        ('product_id', '=', product.id), 
                        ('location_id', '=', dest_location.id)
                    ])
                    available_qty = sum(quants.mapped('available_quantity'))

                    if available_qty:
                        taken_qty = max(0, min(available_qty, to_reserve_qty))
                        to_reserve_qty -= taken_qty
                        if to_reserve_qty <= 0.0:
                            continue
                        
                    # search from other locations availability
                    other_location_availabilities = []
                    quants = Quant._gather_product(product)
                    for src_location in quants.mapped('location_id'):
                        if src_location == dest_location:
                            continue
                        quant_locations = quants.filtered(lambda o: o.location_id == src_location)
                        location_available_qty = sum(quant_locations.mapped('available_quantity'))
                        if location_available_qty <= 0.0:
                            continue
                        qty_taken = min(to_reserve_qty, location_available_qty)
                        in_dates = [o for o in quant_locations.mapped('in_date') if o]
                        date = min(in_dates) if in_dates else False

                        line_values += [{
                            'product_id': product.id,
                            'location_id': src_location.id,
                            'location_dest_id': dest_location.id,
                            'warehouse_id': src_location.get_warehouse().id,
                            'warehouse_dest_id': dest_location.get_warehouse().id,
                            'date': date,
                            'qty': qty_taken
                        }]
                        other_location_availabilities += [(src_location, qty_taken)]
                        to_reserve_qty -= qty_taken
                        if to_reserve_qty <= 0.0:
                            break

                    if to_reserve_qty > 0.0:
                        not_available_qtys[(product, dest_location)]['product_qty'] += qtys['to_reserve'] + qtys['reserved']
                        not_available_qtys[(product, dest_location)]['available'] += available_qty
                        not_available_qtys[(product, dest_location)]['other_locations'] += other_location_availabilities

                else:
                    line_values += [{
                        'product_id': product.id,
                        'location_id': dest_location.id,
                        'location_dest_id': dest_location.id,
                        'warehouse_id': dest_location.get_warehouse().id,
                        'warehouse_dest_id': dest_location.get_warehouse().id,
                        'date': now,
                        'qty': to_reserve_qty
                    }]
            
            if not allow_empty and not_available_qtys:
                debug = True

                info = []
                for (product, location), values in not_available_qtys.items():
                    detail = ''
                    if debug:
                        detail = [
                            '  To Reserve: %s' % values['product_qty'],
                            '  Available: %s' % values['available']
                        ]
                        for other_location, qty_taken in values['other_locations']:
                            detail += ['  %s: %s' % (other_location.display_name, qty_taken)]
                        detail = ': \n%s\n' % ('\n'.join(detail),)
                    
                    info += ['- %s at %s%s' % (product.display_name, location.display_name, detail)]

                info = '\n'.join(info)
                raise ValidationError(_('There is not enough stock to transfer:\n%s' % (info,)))

            group = defaultdict(lambda: [])
            for line_vals in line_values:
                group[line_vals['warehouse_id'], line_vals['warehouse_dest_id']] += [line_vals]

            for (warehouse_id, warehouse_dest_id), vals_list in group.items():
                move_values = []
                location_ids = []
                location_dest_ids = []
                for sequence, line_vals in enumerate(vals_list):
                    product = Product.browse(line_vals['product_id'])
                    
                    move_values += [(0, 0, {
                        'sequence': sequence + 1,
                        'source_location_id': line_vals['location_id'],
                        'destination_location_id': line_vals['location_dest_id'],
                        'product_id': product.id,
                        'description': product.display_name,
                        'qty': line_vals['qty'],
                        'uom': product.uom_id.id,
                        'scheduled_date': now,
                        'analytic_account_group_ids': [(6, 0, analytic_tag_ids.ids)]
                    })]
                    location_ids += [line_vals['location_id']]
                    location_dest_ids += [line_vals['location_dest_id']]

                is_single_source_location = allow_empty
                is_single_destination_location = allow_empty

                location_id = False
                if is_single_source_location:
                    location_id = location_ids and location_ids[0] or False

                location_dest_id = False
                if is_single_destination_location:
                    location_dest_id = location_dest_ids and location_dest_ids[0] or False

                itr_values = {
                    'requested_by': self.env.user.id,
                    'source_warehouse_id': warehouse_id,
                    'destination_warehouse_id': warehouse_dest_id,
                    'company_id': company_id.id,
                    'branch_id': branch_id.id,
                    'scheduled_date': now,
                    'source_document': origin,
                    'product_line_ids': move_values,
                    'is_mrp_transfer_request': True,
                    'analytic_account_group_ids': [(6, 0, analytic_tag_ids.ids)],
                    'is_single_source_location': is_single_source_location,
                    'is_single_destination_location': is_single_destination_location,
                    'source_location_id': location_id,
                    'destination_location_id': location_dest_id,
                }
                res_ids += [InternalTransfer.create(itr_values).id]
        
        action = self.env['ir.actions.actions']._for_xml_id('equip3_inventory_operation.action_internal_transfer_request')
        if len(res_ids) == 1:
            action.update({
                'views':  [(self.env.ref('equip3_inventory_operation.view_form_internal_transfer').id, 'form')], 
                'res_id': res_ids[0],
                'target': 'new',
            })
        else:
            action.update({
                'domain': [('id', 'in', res_ids)],
            })
        
        return action

    def action_material_request(self):
        MaterialRequest = self.env['material.request']
        origin = self._get_origin_moves()

        res_ids = MaterialRequest.search([
            ('source_document', '=', origin),
            ('status', '=', 'draft')
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

                groups = self.env['stock.move'].read_group(
                    [('id', 'in', moves.ids)], 
                    ['product_id', 'product_uom'],
                    ['product_id', 'product_uom'],
                    lazy=False)

                move_values = []
                for sequence, group in enumerate(groups):
                    group_moves = Move.search(group['__domain'])

                    product = Product.browse(group['product_id'][0])
                    product_uom_qty = sum([max([
                        move.product_uom_qty - (move.availability_uom_qty + move.reserved_availability), 
                        0.0]) 
                    for move in group_moves])
                        
                    move_values += [(0, 0, {
                        'description': product.display_name,
                        'product': product.id,
                        'product_unit_measure': group['product_uom'][0],
                        'quantity': product_uom_qty,
                        'destination_warehouse_id': warehouse.id
                    })]

                
                values = {
                    'requested_by': self.env.user.id,
                    'branch_id': branch_id.id,
                    'company_id': company_id.id,
                    'destination_warehouse_id': warehouse.id,
                    'destination_location_id': location_id,
                    'schedule_date': now,
                    'source_document': origin,
                    'product_line': move_values,
                    'analytic_account_group_ids': [(6, 0, analytic_tag_ids.ids)]
                }
                res_ids += [MaterialRequest.create(values).id]

        action = self.env['ir.actions.actions']._for_xml_id('equip3_inventory_operation.material_request_action')
        if len(res_ids) == 1:
            action.update({
                'views':  [(self.env.ref('equip3_inventory_operation.material_request_form_view').id, 'form')], 
                'res_id': res_ids[0],
                'target': 'new',
            })
        else:
            action.update({
                'domain': [('id', 'in', res_ids)],
            })
        
        return action

    def action_change_component(self):
        if self._name == 'mrp.workorder':
            return

        line_ids = [(0, 0, {
            'move_id': move.id,
            'product_id': move.product_id.id,
            'product_uom_qty': move.product_uom_qty,
            'product_uom': move.product_uom.id,
            'production_id': move.raw_material_production_id.id,
            'operation_id': move.operation_id.id,
            'workorder_id': (move.workorder_id or move.mrp_workorder_component_id or self.env['mrp.workorder']).id
        }) for move in self._get_material_moves()]

        change_component_values = {
            'line_ids': line_ids
        }
        
        if self._name == 'mrp.production':
            change_component_values.update({
                'production_ids': [(6, 0, self.ids)],
                'production_id': self.id,
                'hide_mo_field': True,
            })
        elif self._name == 'mrp.plan':
            change_component_values.update({
                'production_ids': [(6, 0, self.mrp_order_ids.ids)],
            })

        return {
            'name': _('Change Material'),
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.change.component.wizard',
            'target': 'new',
            'view_mode': 'form',
            'res_id': self.env['mrp.change.component.wizard'].create(change_component_values).id
        }

    def action_view_model(self, action_name, action_model, action_view, action_domain):
        self.ensure_one()
        if not action_name or not action_model or not action_view or not action_domain:
            return
        result = self.env['ir.actions.actions']._for_xml_id(action_name)
        records = self.env[action_model].search(action_domain)
        if not records:
            return
        if len(records) > 1:
            result['domain'] = [('id', 'in', records.ids)]
        else:
            form_view = [(self.env.ref(action_view).id, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(s, v) for s, v in result['views'] if v != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = records.id
        result['context'] = str(dict(eval(result.get('context', '').strip() or '{}', self._context), create=False))
        return result

    def action_view_transfer_request(self):
        return self.action_view_model(
            'equip3_inventory_operation.action_internal_transfer_request',
            'internal.transfer',
            'equip3_inventory_operation.view_form_internal_transfer',
            [('source_document', '=', self._get_origin_moves()), ('is_mrp_transfer_request', '=', True)],
        )

    def action_view_material_request(self):
        return self.action_view_model(
            'equip3_inventory_operation.material_request_action',
            'material.request',
            'equip3_inventory_operation.material_request_form_view',
            [('source_document', '=', self._get_origin_moves())],
        )
