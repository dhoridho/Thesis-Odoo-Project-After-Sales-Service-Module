from odoo import models, fields, api, _
from odoo.http import request
from odoo.tools import float_round


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def action_view_dashboard_kitchen(self):
        if self.env.user.has_group('equip3_kitchen_accessright_settings.group_central_kitchen_is_a_chef'):
            xml_id = 'equip3_kitchen_operations.action_view_dashboard_kitchen'
        else:
            xml_id = 'equip3_kitchen_operations.action_view_dashboard_kitchen_no_access'
        return self.env['ir.actions.actions']._for_xml_id(xml_id)

    def _prepare_kitchen_context(self):
        context = {
            'from_date': self.env.context.get('from_date', False) or '',
            'to_date': self.env.context.get('to_date', False) or '',
            'warehouse': self.env.context.get('warehouse', False)
        }
        return context

    @api.model
    def retrieve_kitchen_dashboard(self):
        warehouses = {}
        for warehouse in self.env['stock.warehouse'].search([
            ('branch_id', 'in', self._context.get('allowed_branch_ids'))
        ]):
            warehouses[warehouse.id] = warehouse.name

        context = self._prepare_kitchen_context()
        if warehouses.keys() and not context.get('warehouse'):
            context.update({
                'warehouse': list(warehouses.keys())[0],
                'change': True,
            })
        has_access = self.env.user.has_group(
            'equip3_kitchen_accessright_settings.group_central_kitchen_is_a_chef')
        kitchen_context = {'warehouses': warehouses, 'context': context, 'has_access': has_access}
        request.session['kitchen_context'] = context

        return kitchen_context

    @api.depends('stock_move_ids.product_qty', 'stock_move_ids.state')
    @api.depends_context('from_date', 'to_date', 'warehouse')
    def _compute_kitchen_quantities(self):
        products = self.filtered(lambda p: p.type != 'service')
        res = products._compute_kitchen_quantities_dict(
            self._context.get('from_date'),
            self._context.get('to_date')
        )
        for product in products:
            product.kitchen_inventory_quantity = res[product.id]['kitchen_inventory_quantity']
            product.kitchen_safety_stock_qty = res[product.id]['kitchen_safety_stock_qty']
            product.kitchen_to_produce_qty = res[product.id]['kitchen_to_produce_qty']
            product.kitchen_outgoing_qty = res[product.id]['kitchen_outgoing_qty']

        # Services need to be set with 0.0 for all quantities
        services = self - products
        services.kitchen_inventory_quantity = 0.0
        services.kitchen_safety_stock_qty = 0.0
        services.kitchen_to_produce_qty = 0.0
        services.kitchen_outgoing_qty = 0.0

    def _get_kitchen_safety_stock_qty(self, warehouse):
        self.ensure_one()
        domain = [('warehouse_id', '=', warehouse)] if warehouse else []
        safety_stock = self.env['kitchen.safety.stock'].search(domain)
        safety_stock_lines = safety_stock.mapped('stock_line_ids')
        product_stock_lines = safety_stock_lines.filtered(lambda s: s.product_id == self)
        return sum(product_stock_lines.mapped('product_qty'))

    def _compute_kitchen_quantities_dict(self, from_date, to_date):
        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = self._get_domain_locations()
        domain_quant = [('product_id', 'in', self.ids)] + domain_quant_loc

        # only to_date as to_date will correspond to qty_available
        dates_in_the_past = False
        to_date = fields.Datetime.to_datetime(to_date)
        if to_date and to_date < fields.Datetime.now():
            dates_in_the_past = True

        domain_itr_out_loc = []
        for item in domain_move_out_loc:
            try:
                field_name, operator, value = item
                new_field_name = field_name.replace('location_id.', 'source_location_id.')
                new_field_name = new_field_name.replace('location_dest_id.', 'destination_location_id.')
                domain_itr_out_loc += [(new_field_name, operator, value)]
            except Exception as err:
                domain_itr_out_loc += [item]

        domain_move_in = [('product_id', 'in', self.ids)] + domain_move_in_loc
        domain_move_out = [('product_id', 'in', self.ids)] + domain_move_out_loc
        domain_itr_out = [('product_line.is_outlet_order', '=', True), ('product_id', 'in', self.ids)] + domain_itr_out_loc

        domain_move_in_done, domain_move_out_done = [], []
        if dates_in_the_past:
            domain_move_in_done = list(domain_move_in)
            domain_move_out_done = list(domain_move_out)

        if from_date:
            date_date_expected_domain_from = [('date', '>=', from_date)]
            date_internal_transfer_expected_domain_from = [('product_line.scheduled_date', '>=', from_date)]
            domain_move_in += date_date_expected_domain_from
            domain_move_out += date_date_expected_domain_from
            domain_itr_out += date_internal_transfer_expected_domain_from

        if to_date:
            date_date_expected_domain_to = [('date', '<=', to_date)]
            date_internal_transfer_expected_domain_to = [('product_line.scheduled_date', '<=', to_date)]
            domain_move_in += date_date_expected_domain_to
            domain_move_out += date_date_expected_domain_to
            domain_itr_out += date_internal_transfer_expected_domain_to

        Move = self.env['stock.move'].with_context(active_test=False)
        QuantInv = self.env['stock.quant'].with_context(active_test=False, inventory_mode=True)
        ITRLine = self.env['internal.transfer.line'].with_context(active_test=False)

        domain_move_out_todo = [('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))] + domain_move_out
        moves_out_res = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_out_todo, ['product_id', 'product_qty'], ['product_id'], orderby='id'))
        itr_out_res = dict((item['product_id'][0], item['qty']) for item in ITRLine.read_group(domain_itr_out, ['product_id', 'qty'], ['product_id'], orderby='id'))
        quants_inv_res = dict((item['product_id'][0], item.get('inventory_quantity', 0.0)) for item in QuantInv.read_group(domain_quant, ['product_id', 'quantity'], ['product_id'], orderby='id'))

        moves_in_res_past, moves_out_res_past = {}, {}
        if dates_in_the_past:
            # Calculate the moves that were done before now to calculate back in time (as most questions will be recent ones)
            domain_move_in_done = [('state', '=', 'done'), ('date', '>', to_date)] + domain_move_in_done
            domain_move_out_done = [('state', '=', 'done'), ('date', '>', to_date)] + domain_move_out_done
            moves_in_res_past = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_in_done, ['product_id', 'product_qty'], ['product_id'], orderby='id'))
            moves_out_res_past = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_out_done, ['product_id', 'product_qty'], ['product_id'], orderby='id'))

        res = dict()
        for product in self:
            pid = product.id
            if not pid:
                res[pid] = {
                    'kitchen_inventory_quantity': 0.0,
                    'kitchen_safety_stock_qty': 0.0,
                    'kitchen_to_produce_qty': 0.0
                }
                continue

            rounding = product.uom_id.rounding
            res[pid] = {}

            kitchen_inventory_quantity = quants_inv_res.get(pid, 0.0)
            if dates_in_the_past:
                kitchen_inventory_quantity -= moves_in_res_past.get(pid, 0.0) + moves_out_res_past.get(pid, 0.0)

            kitchen_safety_stock_qty = self.browse(pid)._get_kitchen_safety_stock_qty(self.env.context.get('warehouse'))
            res[pid]['kitchen_inventory_quantity'] = float_round(kitchen_inventory_quantity, precision_rounding=rounding)
            res[pid]['kitchen_safety_stock_qty'] = float_round(kitchen_safety_stock_qty, precision_rounding=rounding)
            res[pid]['kitchen_outgoing_qty'] = float_round(moves_out_res.get(pid, 0.0), precision_rounding=rounding) + float_round(itr_out_res.get(pid, 0.0), precision_rounding=rounding)

            Q = res[pid]
            kitchen_to_produce_qty = max(0.0, Q['kitchen_safety_stock_qty'] - Q['kitchen_inventory_quantity'] + Q['kitchen_outgoing_qty'])

            res[pid]['kitchen_to_produce_qty'] = float_round(kitchen_to_produce_qty, precision_rounding=rounding)

        return res

    def action_produce(self):
        self.ensure_one()

        kitchen_context = request.session.get('kitchen_context', dict())
        warehouse_id = kitchen_context.get('warehouse', False)

        kitchen_to_produce_qty = self.env.context.get('kitchen_to_produce_qty', 0.0)

        context = self.env.context.copy()

        context.update({
            'default_create_date': fields.Datetime.now(),
            'default_create_uid': self.env.user.id,
            'default_finished_qty': kitchen_to_produce_qty,
            'default_warehouse_id': warehouse_id,
            'default_bom_id': self.kitchen_bom_id.id,
            'default_branch_id': self.env.branch.id,
            'default_dashboard_to_produce_qty': kitchen_to_produce_qty,
            'readonly_fields': True,
            'return_action': True
        })

        action = {
            'name': "Kitchen Production Record",
            'type': 'ir.actions.act_window',
            'res_model': 'kitchen.production.record',
            'view_mode': 'form',
            'target': 'new',
            'context': context
        }
        return action

    def kitchen_create_next_lot(self, product_qty, expiration_date=False, force_company=False):
        self.ensure_one()

        stock_production_lot = self.env['stock.production.lot'].with_context(force_blank_expiration_date=True)
        company_id = force_company or self.company_id.id or self.env.company.id

        values = {
            'product_id': self.id,
            'company_id': company_id,
            'kitchen_qty': product_qty,
            'kitchen_expiration_date': expiration_date
        }

        if not self.is_sn_autogenerate and not self.is_in_autogenerate:
            values.update({'name': self.env['ir.sequence'].next_by_code('stock.lot.serial')})
            return stock_production_lot.create(values)

        if self.tracking == 'serial':
            digits = self.digits
            seq_to_update = 'current_sequence'
            current_seq = int(float(self.current_sequence))
        else:
            digits = self.in_digits
            seq_to_update = 'in_current_sequence'
            current_seq = int(float(self.in_current_sequence))

        while True:
            auto_sequence = self.product_tmpl_id._get_next_lot_and_serial(current_sequence=current_seq)
            lot_id = stock_production_lot.search([('name', '=', auto_sequence)])
            if not lot_id:
                break
            current_seq += 1

        if not lot_id:
            values.update({'name': auto_sequence})
            lot_id = stock_production_lot.create(values)

        # update for next sequence
        self.write({seq_to_update: str(current_seq + 1).zfill(digits)})

        return lot_id

    def _kitchen_is_auto_generate(self):
        self.ensure_one()
        return (self.tracking == 'serial' and self.is_sn_autogenerate) or (self.tracking == 'lot' and self.is_in_autogenerate)

    def _kitchen_is_manual_generate(self):
        self.ensure_one()
        return (self.tracking == 'serial' and not self.is_sn_autogenerate) or (self.tracking == 'lot' and not self.is_in_autogenerate)

    @api.model
    def assign_kitchen_bom(self, domain):
        BoM = self.env['mrp.bom'].with_context(branch_id=self.env.branch.id, equip_bom_type='kitchen')
        company_id = self.env.company.id
        products = self.search(domain)
        products_with_bom = products.filtered(lambda o: o.kitchen_bom_id)
        for product in products - products_with_bom:
            bom = BoM._bom_find(product=product, company_id=company_id, bom_type='normal')
            if bom:
                product.kitchen_bom_id = bom.id
                products_with_bom |= product
        return products_with_bom.ids
    
    kitchen_inventory_quantity = fields.Float(
        'Kitchen Inventory Quantity', compute='_compute_kitchen_quantities',
        digits='Product Unit of Measure', compute_sudo=False)
    kitchen_safety_stock_qty = fields.Float(
        'Kitchen Safety Stock', compute='_compute_kitchen_quantities',
        digits='Product Unit of Measure', compute_sudo=False)
    kitchen_to_produce_qty = fields.Float(
        'Kitchen To Produce', compute='_compute_kitchen_quantities',
        digits='Product Unit of Measure', compute_sudo=False)
    kitchen_outgoing_qty = fields.Float(
        'Kitchen Outgoing Qty', compute='_compute_kitchen_quantities',
        digits='Product Unit of Measure', compute_sudo=False)
    kitchen_bom_id = fields.Many2one('mrp.bom', string='Kitchen BoM', domain="""[
        ('equip_bom_type', '=', 'kitchen'),
        ('type', '=', 'normal'),
        '|', 
            '&', 
                ('product_id', '=', id), 
                ('product_id.product_tmpl_id.produceable_in_kitchen', '=', True),
            '&', 
                '&', 
                    ('product_id', '=', False), 
                    ('product_tmpl_id.product_variant_ids', '=', id),
                ('product_tmpl_id.produceable_in_kitchen', '=', True),
    ]""")