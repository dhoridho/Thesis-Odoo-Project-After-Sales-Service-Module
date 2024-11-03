import json
import logging
from odoo import models, fields, api, _
from odoo.tools import float_is_zero, float_compare
from odoo.addons.base.models.ir_model import quote
from odoo.exceptions import UserError, ValidationError
from collections import defaultdict

_logger = logging.getLogger(__name__)


class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    account_move_ids = fields.One2many('account.move', 'inventory_id')
    state = fields.Selection(selection_add=[
        ('in_progress', 'Validating'),
        ('done',)
    ])

    # technical fields
    fifo_avco_adjustment_data = fields.Char()

    def _get_inventory_lines_values(self):
        """Return the values of the inventory lines to create for this inventory.

        :return: a list containing the `stock.inventory.line` values to create
        :rtype: list
        """
        self.ensure_one()
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))
        company = self.company_id
        user_id = self.env.user.id
        inventory_id = self.id
        prefill_with_zero = self.prefill_counted_quantity == "zero"

        quants_groups = self._get_quantities()
        product_ids = [vals[0] for vals in quants_groups]

        groupby = ['product_id', 'lot_id']
        if is_cost_per_warehouse:
            groupby += ['warehouse_id']
        svl_dict = self.env['product.product']._query_svl(company, product_ids=product_ids, groupby=groupby)
        
        products = {}
        standard_prices = {}
        if product_ids:
            self.env.cr.execute("""
            SELECT
                pp.id,
                pt.uom_id,
                uu.rounding,
                ip.value_text,
                ip2.value_float,
                pt.categ_id
            FROM
                product_product pp
            LEFT JOIN
                product_template pt
                ON (pt.id = pp.product_tmpl_id)
            LEFT JOIN
                uom_uom uu
                ON (uu.id = pt.uom_id)
            LEFT JOIN
                ir_property ip
                ON (ip.name = 'property_cost_method' AND ip.res_id = 'product.category,' || pt.categ_id AND ip.company_id = %s)
            LEFT JOIN
                ir_property ip2
                ON (ip2.name = 'standard_price' AND ip2.res_id = 'product.product,' || pp.id AND ip.company_id = %s)
            WHERE
                pp.id IN %s
            """, [company.id, company.id, tuple(product_ids)])
            products = {o[0]: o[1:] for o in self.env.cr.fetchall()}

            if is_cost_per_warehouse:
                self.env.cr.execute("""
                SELECT
                    pwp.product_id,
                    pwp.warehouse_id,
                    pwp.standard_price
                FROM
                    product_warehouse_price pwp
                WHERE
                    pwp.product_id IN %s
                """, [tuple(product_ids)])
                standard_prices = {(o[0], o[1]): o[2] for o in self.env.cr.fetchall()}

        values = []
        warehouse_dict = {}
        for (product_id, location_id, lot_id, package_id, owner_id), quantity in quants_groups.items():
            warehouse_id = warehouse_dict.get(location_id, self.env['stock.location'].browse(location_id).get_warehouse().id)
            uom_id, rounding, cost_method, product_standard_price, categ_id = products[product_id]
            now = fields.Datetime.now() # each reacord will have different create/write date

            if cost_method == 'average':
                if is_cost_per_warehouse:
                    key = (product_id, lot_id, warehouse_id)
                else:
                    key = (product_id, lot_id)

                vals_svl_dict = svl_dict.get(key, {})
                quantity_svl = vals_svl_dict.get('quantity', 0.0)
                unit_price = 0.0
                if not float_is_zero(quantity_svl, precision_rounding=rounding):
                    unit_price = vals_svl_dict.get('value', 0.0) / quantity_svl
            else:
                unit_price = product_standard_price
                if is_cost_per_warehouse:
                    unit_price = standard_prices.get((product_id, warehouse_id), 0.0)

            line_values = {
                'inventory_id': inventory_id,
                'product_qty': 0 if prefill_with_zero else quantity,
                'theoretical_qty': quantity,
                'prod_lot_id': lot_id,
                'partner_id': owner_id,
                'product_id': product_id,
                'location_id': location_id,
                'package_id': package_id,
                'product_uom_id': uom_id,
                'unit_price': unit_price,
                'theoretical_unit_price': unit_price,

                # related but stored fields
                'categ_id': categ_id,
                'company_id': company.id,

                # invisible fields
                'inventory_date': now,

                # technical fields
                'create_date': now,
                'write_date': now,
                'create_uid': user_id,
                'write_uid': user_id,
            }
            warehouse_dict[location_id] = warehouse_id
            values.append(line_values)
        
        if self.exhausted:
            values += self._get_exhausted_inventory_lines_vals({(l['product_id'], l['location_id']) for l in values})

        return values

    def _get_exhausted_inventory_lines_vals(self, non_exhausted_set):
        """Return the values of the inventory lines to create if the user
        wants to include exhausted products. Exhausted products are products
        without quantities or quantity equal to 0.

        :param non_exhausted_set: set of tuple (product_id, location_id) of non exhausted product-location
        :return: a list containing the `stock.inventory.line` values to create
        :rtype: list
        """
        self.ensure_one()
        company = self.company_id
        user_id = self.env.user.id

        if self.product_ids:
            products = self.product_ids
        else:
            products = self.env['product.product'].search([
                '|', ('company_id', '=', self.company_id.id), ('company_id', '=', False),
                ('type', '=', 'product'),
                ('active', '=', True)])

        if self.location_ids:
            location_ids = self.location_ids.ids
        else:
            location_ids = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)]).lot_stock_id.ids

        vals = []
        for product in products:
            product_id = product.id
            product_uom_id = product.uom_id.id
            for location_id in location_ids:
                if ((product_id, location_id) not in non_exhausted_set):
                    now = fields.Datetime.now() # each reacord will have different create/write date

                    vals.append({
                        'inventory_id': self.id,
                        'product_id': product_id,
                        'product_uom_id': product_uom_id,
                        'location_id': location_id,
                        'theoretical_qty': 0,

                        # related but stored fields
                        'categ_id': product.categ_id.id,
                        'company_id': company.id,

                        # invisible fields
                        'inventory_date': now,

                        # technical fields
                        'create_date': now,
                        'write_date': now,
                        'create_uid': user_id,
                        'write_uid': user_id,
                    })
        return vals

    def _action_start(self):
        """ Confirms the Inventory Adjustment and generates its inventory lines
        if its state is draft and don't have already inventory lines (can happen
        with demo data or tests).
        """
        freezed_locations = self.env['stock.move']._get_freezed_locations()
        for inventory in self:
            if inventory.state != 'draft':
                continue
            vals = {
                'state': 'confirm',
                'date': fields.Datetime.now()
            }
            if not inventory.line_ids and not inventory.start_empty:
                line_values = inventory._get_inventory_lines_values()
                for line in line_values:
                    if line['location_id'] in freezed_locations:
                        location = self.env['stock.location'].browse(line['location_id'])
                        freeze_source = freezed_locations[line['location_id']]
                        raise ValidationError(_("Can't move from/to location %s, because the location is in freeze status from %s. Stock move can be process after operation is done." % (location.display_name, freeze_source)))
                
                self.env['stock.inventory.line']._query_create(line_values)
            inventory.write(vals)
        
    def action_open_inventory_lines(self):
        action = super(StockInventory, self).action_open_inventory_lines()
        if len(self.product_ids) == 1 and len(self.location_ids) == 1:
            is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))
            company = self.company_id
            product = self.product_ids[0]
            location = self.location_ids[0]
            warehouse_id = location.get_warehouse().id
            if is_cost_per_warehouse:
                product = product.with_context(price_for_warehouse=warehouse_id)
            
            if product.cost_method == 'average':
                quantity_svl = product.quantity_svl
                unit_price = 0.0
                if not float_is_zero(quantity_svl, precision_rounding=product.uom_id.rounding):
                    unit_price = product.value_svl / quantity_svl
            else:
                unit_price = product.standard_price
            
            action['context'].update({
                'default_unit_price': unit_price,
                'default_theoretical_unit_price': unit_price
            })
        return action

    def _action_done(self):
        use_scheduler = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.stock_inventory_validation_scheduler', 'False'))

        negative = next((line for line in self.mapped('line_ids') if line.product_qty < 0 and line.product_qty != line.theoretical_qty), False)
        if negative:
            raise UserError(_(
                'You cannot set a negative product quantity in an inventory line:\n\t%s - qty: %s',
                negative.product_id.display_name,
                negative.product_qty
            ))

        self.action_check()
        self.post_inventory()
        
        if use_scheduler:
            self.line_ids._dump_adjustment_data()
            for inventory in self.filtered(lambda x: x.state not in ('done','cancel')):
                self.env['stock.inventory.log'].create({'inventory_id': inventory.id})
                self.write({'state': 'in_progress'})
        else:
            self.line_ids.cost_adjustment()
            self.line_ids.stock_adjustment()
            self.line_ids.write({'is_validated': True})
            self._done_inventory()
        return True

    def _done_inventory(self):
        self.ensure_one()
        self.write({
            'state': 'done', 
            'date': fields.Datetime.now()
        })

    def post_inventory(self):
        quant_vals_list = []
        for line in self.line_ids:
            virtual_location = line._get_virtual_location()
            for location, factor in zip((line.location_id, virtual_location), (1, -1)):
                quant_vals_list += [{
                    'active': True,
                    'product_id': line.product_id.id,
                    'company_id': line.company_id.id,
                    'location_id': location.id,
                    'lot_id': line.prod_lot_id.id,
                    'package_id': line.package_id.id,
                    'owner_id': line.partner_id.id,
                    'quantity': line.difference_qty * factor,
                    'reserved_quantity': 0.0,
                    'to_assign_in_date': True
                }]
        
        if quant_vals_list:
            self.env['stock.quant']._query_create(quant_vals_list)

            self.env.cr.execute("""
            DO
            $$
            DECLARE
                rec RECORD;
            BEGIN
                FOR rec IN 
                    SELECT * FROM stock_quant WHERE to_assign_in_date IS True
                LOOP 
                    UPDATE stock_quant SET in_date = COALESCE((
                        SELECT 
                            in_date 
                        FROM 
                            stock_quant 
                        WHERE 
                            active IS True AND
                            company_id = rec.company_id AND
                            product_id = rec.product_id AND
                            location_id = rec.location_id AND
                            ((rec.lot_id IS NULL AND lot_id IS NULL) OR (rec.lot_id IS NOT NULL AND lot_id = rec.lot_id)) AND
                            ((rec.package_id IS NULL AND package_id IS NULL) OR (rec.package_id IS NOT NULL AND package_id = rec.package_id)) AND
                            ((rec.owner_id IS NULL AND owner_id IS NULL) OR (rec.owner_id IS NOT NULL AND owner_id = rec.owner_id)) AND
                            (to_assign_in_date IS NULL OR to_assign_in_date IS False)
                        ORDER BY 
                            in_date
                        LIMIT 
                            1
                    ), NOW()) WHERE id = rec.id;
                END LOOP;
            END;
            $$""")
            self.env.cr.execute("UPDATE stock_quant SET to_assign_in_date = NULL WHERE to_assign_in_date iS True")
            self.env['stock.quant']._quant_tasks()
        return True
    
    @api.depends('account_move_ids')
    def _compute_has_account_moves(self):
        for inventory in self:
            inventory.has_account_moves = len(inventory.account_move_ids) > 0

    def action_get_account_moves(self):
        self.ensure_one()
        action = super(StockInventory, self).action_get_account_moves()
        action['domain'] = [('id', 'in', self.account_move_ids.ids)]
        return action

    def action_validate(self):
        if not self.exists():
            return
        self.ensure_one()
        if not self.user_has_groups('stock.group_stock_manager'):
            raise UserError(_("Only a stock manager can validate an inventory adjustment."))
        if self.state not in ('completed', 'approved'):
            raise UserError(_(
                "You can't validate the inventory '%s', maybe this inventory "
                "has been already validated or isn't ready.", self.name))

        res = self._check_tracked_lines()
        if res is not True:
            return res

        self._action_done()
        self.line_ids._check_company()
        self._check_company()
        return True

    def _check_tracked_lines(self):
        self.ensure_one()

        self._cr.execute("""
        SELECT
            sil.product_id AS product_id,
            pt.tracking AS tracking
        FROM
            stock_inventory_line sil
        LEFT JOIN
            product_product pp
            ON (pp.id = sil.product_id)
        LEFT JOIN
            product_template pt
            ON (pt.id = pp.product_tmpl_id)
        WHERE
            sil.id IN %s AND
            pt.tracking IN ('lot', 'serial') AND
            sil.prod_lot_id IS NULL AND
            sil.theoretical_qty != sil.product_qty
        GROUP BY
            sil.product_id,
            pt.tracking
        """, [tuple(self.line_ids.ids)])
        inventory_lines = self._cr.dictfetchall()

        if inventory_lines:
            self._cr.execute("""
            SELECT
                sil.product_qty AS product_qty,
                uu.rounding AS rounding
            FROM
                stock_inventory_line sil
            LEFT JOIN
                product_product pp
                ON (pp.id = sil.product_id)
            LEFT JOIN
                product_template pt
                ON (pt.id = pp.product_tmpl_id)
            LEFT JOIN
                uom_uom uu
                ON (uu.id = sil.product_uom_id)
            WHERE
                sil.id IN %s AND
                pt.tracking = 'serial' AND
                sil.prod_lot_id IS NOT NULL
            """, [tuple(self.line_ids.ids)])
            lines = False
            for res in self._cr.dictfetchall():
                if float_compare(res['product_qty'], 1, precision_rounding=res['rounding']) > 0:
                    lines = True
                    break

            if not lines:
                wiz_lines = [(0, 0, {'product_id': o['product_id'], 'tracking': o['tracking']}) for o in inventory_lines]
                wiz = self.env['stock.track.confirmation'].create({'inventory_id': self.id, 'tracking_line_ids': wiz_lines})
                return {
                    'name': _('Tracked Products in Inventory Adjustment'),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'views': [(False, 'form')],
                    'res_model': 'stock.track.confirmation',
                    'target': 'new',
                    'res_id': wiz.id,
                }
        return True


class StockInventoryLine(models.Model):
    _inherit = 'stock.inventory.line'

    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    unit_price = fields.Monetary(string='Unit Price')
    theoretical_unit_price = fields.Monetary(string='Theoretical Unit Price')
    difference_unit_price = fields.Monetary(compute='_compute_difference_unit_cost')

    is_validated = fields.Boolean()
    log_line_id = fields.Many2one('stock.inventory.log.line', string='Log Line')

    @api.depends('unit_price', 'difference_unit_price')
    def _compute_difference_unit_cost(self):
        for line in self:
            line.difference_unit_price = line.unit_price - line.theoretical_unit_price

    def _get_move_values(self, qty, location_id, location_dest_id, out):
        vals = super(StockInventoryLine, self)._get_move_values(qty, location_id, location_dest_id, out)
        vals['name'] = _('INV:') + (self.inventory_id.display_name or '')
        if not out:
            vals['price_unit'] = self.unit_price

        vals.update({
            'quantity_done': vals['product_uom_qty'],
            'state': 'done',
            'procure_method': 'make_to_stock',
            'inventory_line_int': self.id,
        })

        for move_line_vals in vals.get('move_line_ids', []):
            move_line_vals[-1].update({
                'company_id': vals['company_id'],
                'date': vals['date'],
                'qty_done': vals['product_uom_qty'],
                'state': 'done'
            })
        
        return vals

    def _generate_moves(self):
        vals_list = []
        for line in self:
            virtual_location = line._get_virtual_location()
            rounding = line.product_id.uom_id.rounding
            if float_is_zero(line.difference_qty, precision_rounding=rounding):
                continue
            if line.difference_qty > 0:  # found more than expected
                vals = line._get_move_values(line.difference_qty, virtual_location.id, line.location_id.id, False)
            else:
                vals = line._get_move_values(abs(line.difference_qty), line.location_id.id, virtual_location.id, True)
            vals_list.append(vals)
        return self.env['stock.move']._query_create(vals_list)

    def cost_adjustment(self):
        standard_lines = self.filtered(lambda o: o.product_id.cost_method == 'standard')
        (self - standard_lines).fifo_avco_adjustment()
        standard_lines.standard_adjustment()

    def _dump_adjustment_data(self):
        standard_lines = self.filtered(lambda o: o.product_id.cost_method == 'standard')
        (self - standard_lines)._dump_fifo_avco_adjustment_data()

    def _dump_fifo_avco_adjustment_data(self):
        if not self:
            return
        
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        inventory = self[0].inventory_id
        warehouse = inventory.warehouse_id
        company = inventory.company_id

        warehouse_clause = '= %s' % (warehouse.id,) if is_cost_per_warehouse else 'IS NOT NULL'

        query = """
        SELECT
            svl_line.product_id, 
            svl_line.lot_id, 
            '[' || string_agg('(' || svl_line.location_id::character varying || ',' || svl_line.warehouse_id::character varying || ')', ',') || ']' 
        FROM
            (SELECT
                svl.product_id,
                svll.lot_id, 
                svl.location_id, 
                svl.warehouse_id 
            FROM
                stock_valuation_layer_line svll 
            LEFT JOIN
                stock_valuation_layer svl
                ON (svl.id = svll.svl_id) 
            WHERE
                svl.company_id = %s AND
                svl.product_id IN %s AND
                svl.location_id IS NOT NULL AND
                svl.warehouse_id {warehouse_clause}
            GROUP BY
                svl.product_id, 
                svll.lot_id, 
                svl.location_id, 
                svl.warehouse_id) svl_line
        GROUP BY
            svl_line.product_id, 
            svl_line.lot_id 
        """.format(warehouse_clause=warehouse_clause)

        products = self.mapped('product_id')
        self.env.cr.execute(query, [company.id, tuple(products.ids)])

        groups = {}
        for product_id, lot_id, location_warehouse_ids in self.env.cr.fetchall():
            key = '%s_%s' % (product_id, lot_id or False)
            groups[key] = eval(location_warehouse_ids)

        domain = [
            ('product_id', 'in', products.ids),
            ('location_id', 'in', self.mapped('location_id').ids),
            ('lot_id', 'in', self.mapped('prod_lot_id').ids or [False])
        ]
        groupby = ['product_id', 'warehouse_id', 'location_id', 'lot_id']
        svl_dict = products._query_svl(company, domain=domain, groupby=groupby, key_join=True)
        inventory.fifo_avco_adjustment_data = json.dumps({'groups': groups, 'svl_dict': svl_dict})

    def fifo_avco_adjustment(self):
        if not self:
            return

        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        inventory = self[0].inventory_id
        company = inventory.company_id
        currency = company.currency_id

        if not inventory.fifo_avco_adjustment_data:
            self._dump_fifo_avco_adjustment_data()
        
        data = json.loads(inventory.fifo_avco_adjustment_data or '{}')
        groups = data.get('groups', {})
        svl_dict = data.get('svl_dict', {})

        warehouse_wise = defaultdict(lambda: [])
        for line in self:
            product = line.product_id
            cost_method = product.cost_method
            unit_price = line.unit_price
            line_theoretical_unit_price = line.theoretical_unit_price
            lot = line.prod_lot_id
            line_warehouse_id = line.location_id.get_warehouse().id

            for location_id, warehouse_id in groups.get('%s_%s' % (product.id, lot.id), []):
                theoretical_unit_price = unit_price
                group_svl_dict = svl_dict.get('%s_%s_%s_%s' % (product.id, warehouse_id, location_id, lot.id), {})
                quantity_svl = group_svl_dict.get('quantity', 0.0)

                if cost_method == 'average':
                    if not float_is_zero(quantity_svl, precision_rounding=product.uom_id.rounding):
                        theoretical_unit_price = group_svl_dict.get('value', 0.0) / quantity_svl
                elif cost_method == 'fifo':
                    if warehouse_id != line_warehouse_id:
                        theoretical_unit_price = product.with_context(price_for_warehouse=warehouse_id).standard_price
                    else:
                        theoretical_unit_price = line_theoretical_unit_price
                
                difference_unit_price = unit_price - theoretical_unit_price

                value_to_add = quantity_svl * difference_unit_price
                if currency.is_zero(value_to_add):
                    continue

                warehouse_wise[(company.id, inventory.id, product.id, warehouse_id, location_id)] += [{
                    'value': value_to_add,
                    'lot_id': lot.id,
                    'unit_cost': unit_price
                }]

        svl_vals_list = []
        for (company_id, inventory_id, product_id, warehouse_id, location_id), line_values in warehouse_wise.items():
            product = self.env['product.product'].browse(product_id)

            lot_ids = [o['lot_id'] for o in line_values if o['lot_id']]
            value = sum(o['value'] for o in line_values)
            ref = _('INV:') + (inventory.display_name or '')

            svl_vals_list += [{
                'description': '%s - %s' % (ref, product.name),
                'company_id': company_id,
                'product_id': product.id,
                'warehouse_id': warehouse_id,
                'location_id': location_id,
                'inventory_id': inventory_id,
                'lot_ids': [(6, 0, lot_ids)],
                'quantity': 0,
                'unit_cost': 0,
                'value': value,
                'line_ids': [(0, 0, {
                    'quantity': 0,
                    'unit_cost': o['unit_cost'], # will updated to 0.0 later
                    'value': o['value'],
                    'lot_id': o['lot_id'],
                }) for o in line_values]
            }]
        
        if svl_vals_list:
            stock_valuation_layers = self.env['stock.valuation.layer']._query_create(svl_vals_list)
            stock_valuation_layers._fifo_revaluate()

    def standard_adjustment(self):
        if not self:
            return
        
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))
        
        inventory = self[0].inventory_id
        warehouse = inventory.warehouse_id

        for line in self:
            product = line.product_id
            if is_cost_per_warehouse:
                product = product.with_context(price_for_warehouse=warehouse.id)

            unit_price = line.unit_price
            if not unit_price:
                unit_price = product.standard_price

            """ Let's _change_standard_price do the job """
            product.with_context(inventory_id=inventory.id).write({'standard_price': unit_price})

    def stock_adjustment(self, log_line=None):
        if not self:
            return

        if log_line:
            log_line.state = 'running'

        self.env.cr.execute("""
        SELECT
            sm.id
        FROM
            stock_move sm
        WHERE
            sm.inventory_line_int IN %s
        ORDER BY
            sm.id
        """, [tuple(self.ids)])
        move_ids = [o[0] for o in self.env.cr.fetchall()]
        moves = self.env['stock.move'].browse(move_ids)
        if moves:
            moves.do_pending_valuations()
        
        self.is_validated = True
