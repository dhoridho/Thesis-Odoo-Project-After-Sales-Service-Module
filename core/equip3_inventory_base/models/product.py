from odoo import models, fields, api, _
from odoo.tools import float_is_zero, float_repr
from odoo.exceptions import ValidationError, UserError
from collections import OrderedDict
from .fields import ProductStandardPrice
from collections import defaultdict
from odoo.osv import expression


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def create(self, vals):
        if 'standard_price' in vals:
            self = self.with_context(disable_auto_svl=True)
        return super(ProductTemplate, self).create(vals)

    @api.model
    def _default_is_cost_per_warehouse(self):
        return eval(self.env['ir.config_parameter'].sudo().get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

    warehouse_price_ids = fields.One2many('product.warehouse.price', compute='_compute_warehouse_standard_price', inverse='_set_warehouse_standard_price')
    warehouse_price_count = fields.Integer(compute='_compute_warehouse_standard_price')
    is_cost_per_warehouse = fields.Boolean(compute='_compute_is_cost_per_warehouse', default=_default_is_cost_per_warehouse)

    """ added `price_for_warehouse' depends_context """
    standard_price = fields.Float(depends_context=['company', 'price_for_warehouse'])

    def _compute_is_cost_per_warehouse(self):
        self.is_cost_per_warehouse = self._default_is_cost_per_warehouse()

    def _is_invisible_standard_price(self):
        return super(ProductTemplate, self)._is_invisible_standard_price() or self.is_cost_per_warehouse

    @api.onchange('is_cost_per_warehouse')
    def _onchange_is_cost_per_warehouse_trigger_attrs(self):
        self._compute_attrs_standard_price()

    @api.depends('product_variant_ids', 'product_variant_ids.warehouse_price_ids')
    def _compute_warehouse_standard_price(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.warehouse_price_ids = [(6, 0, template.product_variant_ids.warehouse_price_ids.ids)]
        for template in (self - unique_variants):
            template.warehouse_price_ids = [(5,)]

        for template in self:
            template.warehouse_price_count = len(template.warehouse_price_ids)

    def _set_warehouse_standard_price(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.warehouse_price_ids = [(6, 0, template.warehouse_price_ids.ids)]

    def action_view_warehouse_standard_price(self):
        self.ensure_one()
        view_xml_id = 'view_product_warehouse_price_tree_editable' if self.cost_method == 'standard' else 'view_product_warehouse_price_tree'
        return {
            'name': 'Warehouse Costs',
            'type': 'ir.actions.act_window',
            'res_model': 'product.warehouse.price',
            'target': 'current',
            'view_mode': 'tree',
            'view_id': self.env.ref('equip3_inventory_base.%s' % view_xml_id).id,
            'domain': [('product_id', 'in', self.product_variant_ids.ids)],
            'context': {
                'default_company_id': self.env.company.id, # should follow active company not self.company_id
                'default_product_id': self.product_variant_id.id,
                'invisible_company': len(self.env.companies) == 1
            }
        }


class ProductProduct(models.Model):
    _inherit = 'product.product'

    warehouse_price_ids = fields.One2many('product.warehouse.price', 'product_id', groups='base.group_user')
    warehouse_price_count = fields.Integer(compute='_compute_warehouse_standard_price')

    standard_price = ProductStandardPrice(
        'Cost', company_dependent=True,
        digits='Product Price',
        groups="base.group_user",
        help="""In Standard Price & AVCO: value of the product (automatically computed in AVCO).
        In FIFO: value of the next unit that will leave the stock (automatically computed).
        Used to value the product when the purchase cost is not known (e.g. inventory adjustment).
        Used to compute margins on sale orders.""")

    def write(self, vals):
        if 'standard_price' in vals:
            is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))
            if is_cost_per_warehouse:
                if not self.env.context.get('price_for_warehouse'):
                    done_moves = self.env['stock.move'].search([('product_id', 'in', self.ids), ('state', '=', 'done')])
                    if done_moves:
                        raise UserError(_("You cannot change general product cost while cost is per warehouse. Edit via warehouse costs instead!"))
                    else:
                        self = self.with_context(disable_auto_svl=True)
        return super(ProductProduct, self).write(vals)

    def _is_invisible_standard_price(self):
        return super(ProductProduct, self)._is_invisible_standard_price() or self.is_cost_per_warehouse

    @api.onchange('is_cost_per_warehouse')
    def _onchange_is_cost_per_warehouse_trigger_attrs(self):
        self._compute_attrs_standard_price()

    def _get_valued_warehouse(self, company_id):
        self.ensure_one()
        self._cr.execute("""
            SELECT
                DISTINCT svl.warehouse_id
            FROM
                stock_valuation_layer svl
            WHERE
                svl.company_id = %s AND 
                svl.product_id = %s AND
                svl.warehouse_id IS NOT NULL
            """, [company_id, self.id])
        return [o[0] for o in self.env.cr.fetchall()]

    @api.model
    def _change_standard_price_domain(self, **kw):
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))
        domain = [
            ('product_id', '=', kw.get('product_id', False)),
            ('company_id', '=', kw.get('company_id', self.env.company.id))
        ]
        if is_cost_per_warehouse:
            domain += [('warehouse_id', '=', kw.get('warehouse_id', False))]
        return domain

    @api.model
    def _change_standard_price_where(self, **kw):
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))
        where = [
            'svl.product_id = %s' % kw.get('product_id', False),
            'svl.company_id = %s' % kw.get('company_id', self.env.company.id)
        ]
        if is_cost_per_warehouse:
            where += ['svl.warehouse_id = %s' % kw.get('warehouse_id', False)]
        return ' AND '.join(where)

    def _change_standard_price_prepare_svl_vals(self, company_id, warehouse_id, location_id, line_values):
        self.ensure_one()

        inventory = self.env['stock.inventory'].browse(self.env.context.get('inventory_id', False))

        description = _('Product value manually modified')
        if inventory.exists():
            description = _('INV:') + (inventory.display_name or '')
            description = '%s - %s' % (description, self.name)
        elif self.env.context.get('is_product_price_update', False):
            description = _('Product value automatically modified')

        value = 0.0
        lot_ids = []
        for line_vals in line_values:
            value += line_vals[-1]['value']
            if line_vals[-1]['lot_id']:
                lot_ids += [line_vals[-1]['lot_id']]
            line_vals[-1]['description'] = description

        return  {
            'company_id': company_id,
            'product_id': self.id,
            'description': description,
            'value': value,
            'quantity': 0,
            'unit_cost': 0,
            'warehouse_id': warehouse_id,
            'location_id': location_id,
            'lot_ids': [(6, 0, lot_ids)],
            'inventory_id': inventory.id,
            'line_ids': line_values
        }

    def _change_standard_price(self, new_price):
        """Helper to create the stock valuation layers and the account moves
        after an update of standard price.

        :param new_price: new standard price
        """
        # Handle stock valuation layers.
        company_id = self.env.company
        warehouse_id = self.env.context.get('price_for_warehouse', False)
        is_product_price_update = self.env.context.get('is_product_price_update', False)

        if self.filtered(lambda p: p.valuation == 'real_time') and not self.env['stock.valuation.layer'].check_access_rights('read', raise_exception=False):
            raise UserError(_("You cannot update the cost of a product in automated valuation as it leads to the creation of a journal entry, for which you don't have the access rights."))

        svl_vals_list = []
        for product in self:

            if not is_product_price_update and product.cost_method not in ('standard', 'average'):
                continue

            where = self._change_standard_price_where(
                product_id=product.id, company_id=company_id.id, warehouse_id=warehouse_id)
            
            self._cr.execute("""
            SELECT
                svl.warehouse_id,
                svl.location_id,
                svll.lot_id,
                SUM(svll.value) AS value,
                SUM(svll.quantity) AS quantity
            FROM
                stock_valuation_layer_line svll
            LEFT JOIN
                stock_valuation_layer svl
                ON (svl.id = svll.svl_id)
            WHERE
                {where}
            GROUP BY
                svl.warehouse_id,
                svl.location_id,
                svll.lot_id
            """.format(where=where))

            lines_dict = defaultdict(lambda: [])
            for warehouse_id, location_id, lot_id, lot_value, lot_quantity in self._cr.fetchall():
                if float_is_zero(lot_quantity, precision_rounding=product.uom_id.rounding):
                    continue

                lot_standard_price = lot_value / lot_quantity
                diff = new_price - lot_standard_price

                value = company_id.currency_id.round(lot_quantity * diff)
                if company_id.currency_id.is_zero(value):
                    continue
                
                lines_dict[(warehouse_id, location_id)] += [(0, 0, {
                    'quantity': 0,
                    'unit_cost': 0,
                    'value': value,
                    'lot_id': lot_id or False,
                    'description': _('Product value manually modified (from %s to %s)') % (lot_standard_price, new_price)
                })]

            for (warehouse_id, location_id), line_values in lines_dict.items():
                svl_vals_list += [product._change_standard_price_prepare_svl_vals(
                    company_id.id, warehouse_id, location_id, line_values)]

        if not svl_vals_list:
            return
        
        stock_valuation_layers = self.env['stock.valuation.layer'].sudo()._query_create(svl_vals_list)

        # Handle account moves.
        am_vals_list = []
        for stock_valuation_layer in stock_valuation_layers:
            product = stock_valuation_layer.product_id
            if product.type != 'product' or product.valuation != 'real_time':
                continue
            am_vals_list.append(stock_valuation_layer._change_standard_price_prepare_account_move_vals(new_price))

        self.env['account.move'].sudo()._query_create(am_vals_list)

    @api.depends('stock_valuation_layer_ids')
    @api.depends_context('to_date', 'company', 'lot_id', 'price_for_warehouse', 'price_for_location')
    def _compute_value_svl(self):
        if not self.ids:
            self.value_svl = 0.0
            self.quantity_svl = 0.0
            return
        
        company = self.env.company
        currency = company.currency_id

        domain = [
            ['company_id', '=', company.id],
            ['product_id', 'in', self.ids]
        ]

        if self.env.context.get('lot_id'):
            domain += [['lot_id', '=', self.env.context['lot_id']]]
        if self.env.context.get('price_for_warehouse'):
            domain += [['warehouse_id', '=', self.env.context['price_for_warehouse']]]
        if self.env.context.get('price_for_location'):
            domain += [['location_id', '=', self.env.context['price_for_location']]]
        if self.env.context.get('to_date'):
            to_date = fields.Datetime.to_datetime(self.env.context['to_date'])
            domain += [['create_date', '<=', to_date]]

        group = self._query_svl(company, domain=domain)

        for product in self:
            product_group = group.get(product.id, {})
            product.value_svl = currency.round(product_group.get('value', 0.0))
            product.quantity_svl = product_group.get('quantity', 0.0)

    def _query_svl(self, company, product_ids=None, domain=[], groupby=['product_id'], key_join=False):
        svl_value = defaultdict(lambda: {'value': 0.0, 'quantity': 0.0})
        product_ids = product_ids or self.ids

        if not product_ids:
            return svl_value

        svl_line_fields = self.env['stock.valuation.layer.line']._fields

        groupby_fields = []
        field_names = []
        for field_name in (groupby or []):
            related = svl_line_fields[field_name].related
            if related:
                groupby_fields += ['"stock_valuation_layer_line__%s"."%s"' % (related[0], field_name)]
            else:
                groupby_fields += ['"stock_valuation_layer_line"."%s"' % field_name]
            field_names += [field_name]

        select = groupby_fields + [
            'SUM("stock_valuation_layer_line"."value") AS value', 
            'SUM("stock_valuation_layer_line"."quantity") AS quantity'
        ]

        select = ', '.join(select)
        groupby = ', '.join(groupby_fields)

        default_domain = [
            ['company_id', '=', company.id],
            ['product_id', 'in', product_ids]
        ]
        if domain:
            default_domain = expression.AND([default_domain, domain])

        query = self.env['stock.valuation.layer.line']._where_calc(default_domain)
        where = query.where_clause[0]

        self._cr.execute("""
        SELECT
            {select}
        FROM
            "stock_valuation_layer_line"
        LEFT JOIN
            "stock_valuation_layer" AS "stock_valuation_layer_line__svl_id"
            ON ("stock_valuation_layer_line__svl_id"."id" = "stock_valuation_layer_line"."svl_id")
        WHERE
            {where}
        GROUP BY
            {groupby}
        """.format(select=select, where=where, groupby=groupby), query._where_params)

        for record in self._cr.dictfetchall():
            key = []
            for field_name in field_names:
                key += [record[field_name] or False]
            
            if not key_join:
                key = key[0] if len(key) == 1 else tuple(key)
            else:
                key = '_'.join(str(k) for k in key)
            svl_value[key]['value'] += record['value']
            svl_value[key]['quantity'] += record['quantity']

        return svl_value

    @api.depends('warehouse_price_ids')
    def _compute_warehouse_standard_price(self):
        for product in self:
            product.warehouse_price_count = len(product.warehouse_price_ids)

    def _price_line(self, warehouse_id):
        self.ensure_one()
        price_line = self.env['product.warehouse.price'].sudo().search([
            ('company_id', '=', self.env.company.id),
            ('product_id', '=', self.id),
            ('warehouse_id', '=', warehouse_id)
        ], limit=1)
        if not price_line:
            price_line = self.env['product.warehouse.price'].sudo().create({
                'product_id': self.id,
                'company_id': self.env.company.id,
                'warehouse_id': warehouse_id,
                'standard_price': 0.0
            })
        return price_line

    def action_view_warehouse_standard_price(self):
        self.ensure_one()
        view_xml_id = 'view_product_warehouse_price_tree_editable' if self.cost_method == 'standard' else 'view_product_warehouse_price_tree'
        return {
            'name': 'Warehouse Costs',
            'type': 'ir.actions.act_window',
            'res_model': 'product.warehouse.price',
            'target': 'current',
            'view_mode': 'tree',
            'view_id': self.env.ref('equip3_inventory_base.%s' % view_xml_id).id,
            'domain': [('product_id', '=', self.id)],
            'context': {
                'default_company_id': self.env.company.id, # should follow active company not self.company_id
                'default_product_id': self.id,
                'invisible_company': len(self.env.companies) == 1
            }
        }

    @api.model
    def ensure_context(self, method_name, context_name):
        if context_name not in self.env.context:
            raise ValidationError(_('Technical issue: `%s` now require `%s` context!' % (method_name, context_name)))
        return self.env.context[context_name]

    def _prepare_in_svl_vals(self, quantity, unit_cost):
        move = self.ensure_context('_prepare_in_svl_vals', 'move')
        cost_method = self.cost_method

        svl_qty = 0.0
        svl_value = 0.0
        line_values = []
        for move_line in move._get_valued_move_lines():
            move_line_unit_cost = move_line.price_unit

            picked_unit_cost = move_line_unit_cost or unit_cost
            line_qty = move_line.product_uom_id._compute_quantity(move_line.qty_done, move_line.product_id.uom_id)
            line_value = picked_unit_cost * line_qty
            
            line_values += [(0, 0, move_line._prepare_in_svl_vals(line_qty, picked_unit_cost))]
            svl_qty += line_qty
            svl_value += line_value

        svl_unit_cost = 0.0
        if not float_is_zero(svl_qty, precision_rounding=self.uom_id.rounding):
            svl_unit_cost = svl_value / svl_qty

        res = super(ProductProduct, self)._prepare_in_svl_vals(quantity, svl_unit_cost)
        res['line_ids'] = line_values
        return res

    def _prepare_out_svl_vals(self, quantity, company):
        self.ensure_one()
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        move = self.ensure_context('_prepare_out_svl_vals', 'move')
        warehouse_id = move._warehouse_id()
        currency = self.env.company.currency_id

        quantity = -1 * quantity
        self_contexed = self
        if is_cost_per_warehouse:
            self_contexed = self.with_context(price_for_warehouse=warehouse_id)
        standard_price = self_contexed.standard_price

        vals = {
            'product_id': self.id,
            'value': quantity * standard_price,
            'unit_cost': standard_price,
            'quantity': quantity,
        }

        source_line_values = []
        rounding_error = 0.0
        if self.cost_method in ('average', 'fifo'):
            fifo_vals = self._run_fifo(abs(quantity), company)
            source_line_values = fifo_vals.pop('source_line_values')
            vals['remaining_qty'] = fifo_vals.get('remaining_qty')

            # In case of AVCO, fix rounding issue of standard price when needed.
            if self.cost_method == 'average':
                rounding_error = currency.round(standard_price * self_contexed.quantity_svl - self_contexed.value_svl)

                if rounding_error:
                    # If it is bigger than the (smallest number of the currency * quantity) / 2,
                    # then it isn't a rounding error but a stock valuation error, we shouldn't fix it under the hood ...
                    if abs(rounding_error) <= (abs(quantity) * currency.rounding) / 2:
                        vals['value'] += rounding_error
                        vals['rounding_adjustment'] = '\nRounding Adjustment: %s%s %s' % (
                            '+' if rounding_error > 0 else '',
                            float_repr(rounding_error, precision_digits=currency.decimal_places),
                            currency.symbol
                        )
            if self.cost_method == 'fifo':
                vals.update(fifo_vals)

        line_values = []
        for move_line in move._get_valued_move_lines():
            qty_to_take = move_line.product_uom_id._compute_quantity(move_line.qty_done, move_line.product_id.uom_id)

            for source_line in source_line_values:
                qty_taken_from_source = min(qty_to_take, source_line['quantity'])
                if float_is_zero(qty_taken_from_source, precision_rounding=self.uom_id.rounding):
                    break
                if self.cost_method != 'fifo':
                    source_line.update({'unit_cost': vals['unit_cost']})
                line_values += [(0, 0, move_line._prepare_out_svl_vals(qty_taken_from_source, source_line))]
                qty_to_take -= qty_taken_from_source
                source_line['quantity'] -= qty_taken_from_source

            if not float_is_zero(qty_to_take, precision_rounding=self.uom_id.rounding):
                # minus stock
                line_values += [(0, 0, move_line._prepare_out_svl_vals(-qty_to_take, vals))]

            source_line_values = [v for v in source_line_values if v['quantity']]

        if 'rounding_adjustment' in vals and not currency.is_zero(rounding_error) and line_values:
            line_values[-1][-1].update({
                'value': line_values[-1][-1]['value'] + rounding_error,
                'rounding_error': rounding_error
            })

        vals.update({'line_ids': line_values})
        return vals

    def _simulate_fifo(self, quantity, company, lot_ids, warehouse_id):
        self.ensure_one()
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        # Find back incoming stock valuation layers (called candidates here) to value `quantity`.
        qty_to_take_on_candidates = quantity

        where = [
            'svl.product_id = %s' % self.id,
            'svl.remaining_qty > 0.0',
            'svl.company_id = %s' % company.id,
        ]
        if is_cost_per_warehouse:
            where += ['svl.warehouse_id = %s' % warehouse_id]
        where = ' AND '.join(where)

        self._cr.execute("""
        SELECT
            svll.id,
            svll.remaining_qty,
            svll.remaining_value,
            svll.unit_cost,
            svll.lot_id
        FROM
            stock_valuation_layer_line svll
        LEFT JOIN
            stock_valuation_layer svl
            ON (svl.id = svll.svl_id)
        WHERE
            {where}
        ORDER BY
            svll.create_date
        """.format(where=where))
        
        candidates = self._cr.dictfetchall()

        new_standard_price = 0
        tmp_value = 0  # to accumulate the value taken on the candidates

        candidates_dict = OrderedDict([(str(cnd['id']), {
            'remaining_qty': cnd['remaining_qty'],
            'remaining_value': cnd['remaining_value'],
            'unit_cost': cnd['unit_cost'],
            'lot_id': cnd['lot_id'] or False
        }) for cnd in candidates])

        currency = company.currency_id

        for candidate in candidates:
            cid = str(candidate['id'])
            if candidates_dict[cid]['lot_id'] not in lot_ids:
                continue
            qty_taken_on_candidate = min(qty_to_take_on_candidates, candidates_dict[cid]['remaining_qty'])

            candidate_unit_cost = candidates_dict[cid]['remaining_value'] / candidates_dict[cid]['remaining_qty']
            new_standard_price = candidate_unit_cost
            value_taken_on_candidate = qty_taken_on_candidate * candidate_unit_cost
            value_taken_on_candidate = currency.round(value_taken_on_candidate)
            new_remaining_value = candidates_dict[cid]['remaining_value'] - value_taken_on_candidate

            candidates_dict[cid]['remaining_qty'] = candidates_dict[cid]['remaining_qty'] - qty_taken_on_candidate
            candidates_dict[cid]['remaining_value'] = new_remaining_value

            qty_to_take_on_candidates -= qty_taken_on_candidate
            tmp_value += value_taken_on_candidate

            if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
                if float_is_zero(candidates_dict[cid]['remaining_qty'], precision_rounding=self.uom_id.rounding):
                    next_candidates = False
                    for cnd_id, cnd_vals in candidates_dict.items():
                        if cnd_vals['remaining_qty'] > 0:
                            next_candidates = candidates_dict[cnd_id]
                            break
                    new_standard_price = next_candidates and next_candidates['unit_cost'] or new_standard_price
                break

        # Update the standard price with the price of the last used candidate, if any.
        self_contexed = self
        if is_cost_per_warehouse:
            self_contexed = self.with_context(price_for_warehouse=warehouse_id)
        
        self_standard_price = self_contexed.standard_price
        if new_standard_price and self.cost_method == 'fifo':
            self_standard_price = new_standard_price

        return self_standard_price

    @api.model
    def _run_fifo_init_line_values(self):
        return {
            'quantity': 0.0, 
            'value': 0.0
        }

    @api.model
    def _run_fifo_update_line_values(self, **kwargs):
        lot_value = kwargs.get('lot_value', self._run_fifo_init_line_values())
        qty_taken_on_candidate = kwargs.get('qty_taken_on_candidate', 0.0)
        value_taken_on_candidate = kwargs.get('value_taken_on_candidate', 0.0)
        return {
            'quantity': lot_value.get('quantity', 0.0) - qty_taken_on_candidate,
            'value': lot_value.get('value', 0.0) - value_taken_on_candidate
        }

    @api.model
    def _run_fifo_parameters(self):
        return [
            'lot_value',
            'qty_taken_on_candidate',
            'value_taken_on_candidate'
        ]

    def _run_fifo(self, quantity, company):
        self.ensure_one()
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        move = self.ensure_context('_run_fifo', 'move')
        move_lines = move._get_valued_move_lines()

        lot_ids = move._ordered_lots()
        warehouse_id = self.env.context.get('price_for_warehouse', False)

        # Find back incoming stock valuation layers (called candidates here) to value `quantity`.
        qty_to_take_on_candidates = quantity

        domain = [
            ('product_id', '=', self.id),
            ('remaining_qty', '>', 0),
            ('company_id', '=', company.id),
        ]
        if is_cost_per_warehouse:
            domain += [('warehouse_id', '=', warehouse_id)]

        candidates = self.env['stock.valuation.layer.line'].sudo().search(domain)
        new_standard_price = 0
        tmp_value = 0  # to accumulate the value taken on the candidates
        source_line_values = []
        for candidate in candidates:
            if candidate.lot_id.id not in lot_ids:
                continue
            
            qty_taken_on_candidate = min(qty_to_take_on_candidates, candidate.remaining_qty)

            candidate_unit_cost = candidate.remaining_value / candidate.remaining_qty
            new_standard_price = candidate_unit_cost
            value_taken_on_candidate = qty_taken_on_candidate * candidate_unit_cost
            value_taken_on_candidate = candidate.currency_id.round(value_taken_on_candidate)
            new_remaining_value = candidate.remaining_value - value_taken_on_candidate

            candidate_vals = {
                'remaining_qty': candidate.remaining_qty - qty_taken_on_candidate,
                'remaining_value': new_remaining_value,
            }

            source_line_values += [candidate._prepare_candidate_values(quantity=qty_taken_on_candidate)]

            candidate.write(candidate_vals)
            candidate.svl_id.write({
                'remaining_qty': candidate.svl_id.remaining_qty - qty_taken_on_candidate,
                'remaining_value': candidate.svl_id.remaining_value - value_taken_on_candidate
            })

            qty_to_take_on_candidates -= qty_taken_on_candidate
            tmp_value += value_taken_on_candidate

            if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
                if float_is_zero(candidate.remaining_qty, precision_rounding=self.uom_id.rounding):
                    next_candidates = candidates.filtered(lambda svl: svl.remaining_qty > 0)
                    new_standard_price = next_candidates and next_candidates[0].unit_cost or new_standard_price
                break

        # Update the standard price with the price of the last used candidate, if any.
        if new_standard_price and self.cost_method == 'fifo':
            self.sudo().with_company(company.id).with_context(disable_auto_svl=True).standard_price = new_standard_price

        # If there's still quantity to value but we're out of candidates, we fall in the
        # negative stock use case. We chose to value the out move at the price of the
        # last out and a correction entry will be made once `_fifo_vacuum` is called.
        vals = {}
        if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
            vals = {
                'value': -tmp_value,
                'unit_cost': tmp_value / quantity,
            }
        else:
            assert qty_to_take_on_candidates > 0
            last_fifo_price = new_standard_price or self.standard_price
            negative_stock_value = last_fifo_price * -qty_to_take_on_candidates
            tmp_value += abs(negative_stock_value)
            vals = {
                'remaining_qty': -qty_to_take_on_candidates,
                'value': -tmp_value,
                'unit_cost': last_fifo_price,
            }

        vals['source_line_values'] = source_line_values
        return vals

    def _run_fifo_vacuum(self, company=None):
        self.ensure_one()
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        moves = self.ensure_context('_run_fifo_vacuum', 'active_stock_moves')
        lot_ids = moves._ordered_lots()
        warehouse_ids = [] if not is_cost_per_warehouse else [move._warehouse_id() for move in moves]

        if company is None:
            company = self.env.company

        def clause(record_ids, column):
            if False in record_ids:
                not_null_records = [o for o in record_ids if o]
                if not not_null_records:
                    return '%s IS NULL' % (column,)
                return '(%s IS NULL OR %s)' % (column, clause(not_null_records, column))
            if len(record_ids) == 1:
                return '%s = %s' % (column, record_ids[0])
            return '%s IN %s' % (column, tuple(record_ids))

        lot_clause = clause(lot_ids, 'svll.lot_id')

        where_clause = [
            'svll.remaining_qty < 0.0',
            'svl.product_id = %s' % (self.id,),
            'svl.stock_move_id IS NOT NULL',
            'svl.company_id = %s' % (company.id,),
            lot_clause
        ]

        if is_cost_per_warehouse:
            where_clause += [clause(warehouse_ids, 'svl.warehouse_id')]

        where_clause = ' AND '.join(where_clause)

        query = """
        SELECT
            svll.id
        FROM
            stock_valuation_layer_line svll
        LEFT JOIN
            stock_valuation_layer svl
            ON (svl.id = svll.svl_id)
        WHERE
            {where}
        ORDER BY
            svll.id
        """.format(where=where_clause)

        self.env.cr.execute(query)
        svl_lines_to_vacuum = self.env['stock.valuation.layer.line'].browse(o[0] for o in self.env.cr.fetchall())

        if not svl_lines_to_vacuum:
            return

        where_clause = [
            'svll.remaining_qty > 0.0',
            'svll.create_date > %s',
            'svl.product_id = %s' % (self.id,),
            'svl.company_id = %s' % (company.id,),
            lot_clause
        ]

        if is_cost_per_warehouse:
            where_clause += [clause(warehouse_ids, 'svl.warehouse_id')]

        where_clause = ' AND '.join(where_clause)

        query = """
        SELECT
            svll.id
        FROM
            stock_valuation_layer_line svll
        LEFT JOIN
            stock_valuation_layer svl
            ON (svl.id = svll.svl_id)
        WHERE
            {where}
        ORDER BY
            svll.id
        """.format(where=where_clause)

        params = (svl_lines_to_vacuum[0].create_date,)

        self.env.cr.execute(query, params)

        all_candidates = self.env['stock.valuation.layer.line'].browse(o[0] for o in self.env.cr.fetchall())

        svls_to_vacuum = {svl: {
            'value': 0.0,
            'lines': {line: 0.0 for line in svl.line_ids}
        } for svl in svl_lines_to_vacuum.mapped('svl_id')}

        for svl_line_to_vacuum in svl_lines_to_vacuum:
            # We don't use search to avoid executing _flush_search and to decrease interaction with DB
            candidates = all_candidates.filtered(
                lambda r: r.create_date > svl_line_to_vacuum.create_date
                or r.create_date == svl_line_to_vacuum.create_date
                and r.id > svl_line_to_vacuum.id
            )
            if not candidates:
                break
            qty_to_take_on_candidates = abs(svl_line_to_vacuum.remaining_qty)
            qty_taken_on_candidates = 0
            tmp_value = 0
            for candidate in candidates:
                qty_taken_on_candidate = min(candidate.remaining_qty, qty_to_take_on_candidates)
                qty_taken_on_candidates += qty_taken_on_candidate

                candidate_unit_cost = candidate.remaining_value / candidate.remaining_qty
                value_taken_on_candidate = qty_taken_on_candidate * candidate_unit_cost
                value_taken_on_candidate = candidate.currency_id.round(value_taken_on_candidate)
                new_remaining_value = candidate.remaining_value - value_taken_on_candidate

                candidate_vals = {
                    'remaining_qty': candidate.remaining_qty - qty_taken_on_candidate,
                    'remaining_value': new_remaining_value
                }

                candidate.write(candidate_vals)
                candidate.svl_id.write({
                    'remaining_qty': candidate.svl_id.remaining_qty - qty_taken_on_candidate,
                    'remaining_value': candidate.svl_id.remaining_value - value_taken_on_candidate,
                })
                if not (candidate.remaining_qty > 0):
                    all_candidates -= candidate

                qty_to_take_on_candidates -= qty_taken_on_candidate
                tmp_value += value_taken_on_candidate
                if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
                    break

            # Get the estimated value we will correct.
            if not float_is_zero(svl_line_to_vacuum.remaining_qty, precision_rounding=self.uom_id.rounding):
                svl_line_unit_cost = svl_line_to_vacuum.remaining_value / svl_line_to_vacuum.remaining_qty
            else:
                svl_line_unit_cost = svl_line_to_vacuum.unit_cost

            remaining_value_before_vacuum = svl_line_unit_cost * qty_taken_on_candidates
            new_remaining_qty = svl_line_to_vacuum.remaining_qty + qty_taken_on_candidates
            new_remaining_value = new_remaining_qty * svl_line_unit_cost

            corrected_value = remaining_value_before_vacuum - tmp_value
            svl_line_to_vacuum.write({
                'remaining_qty': new_remaining_qty,
                'remaining_value': new_remaining_value
            })
            svl_line_to_vacuum.svl_id.write({
                'remaining_qty': svl_line_to_vacuum.svl_id.remaining_qty + qty_taken_on_candidates,
                'remaining_value': (svl_line_to_vacuum.svl_id.remaining_qty + qty_taken_on_candidates) * svl_line_unit_cost
            })

            # Don't create a layer or an accounting entry if the corrected value is zero.
            if svl_line_to_vacuum.currency_id.is_zero(corrected_value):
                continue

            svls_to_vacuum[svl_line_to_vacuum.svl_id]['value'] += corrected_value
            svls_to_vacuum[svl_line_to_vacuum.svl_id]['lines'][svl_line_to_vacuum] = corrected_value

        for svl_to_vacuum, svl_to_vacuum_values in svls_to_vacuum.items():
            corrected_value = svl_to_vacuum_values['value']

            if svl_to_vacuum.currency_id.is_zero(corrected_value):
                continue

            corrected_value = svl_to_vacuum.currency_id.round(corrected_value)
            move = svl_to_vacuum.stock_move_id

            line_values = []
            line_lot_ids = []
            for line_to_vacuum, line_corrected_value in svl_to_vacuum_values['lines'].items():
                if line_to_vacuum.currency_id.is_zero(line_corrected_value):
                    continue
                line_values += [(0, 0, {
                    'value': line_corrected_value,
                    'unit_cost': 0,
                    'quantity': 0,
                    'remaining_qty': 0,
                    'lot_id': line_to_vacuum.lot_id.id,
                })]
                if line_to_vacuum.lot_id:
                    line_lot_ids += [line_to_vacuum.lot_id.id]

            vals = {
                'product_id': self.id,
                'value': corrected_value,
                'unit_cost': 0,
                'quantity': 0,
                'remaining_qty': 0,
                'stock_move_id': move.id,
                'company_id': move.company_id.id,
                'description': 'Revaluation of %s (negative inventory)' % move.picking_id.name or move.name,
                'stock_valuation_layer_id': svl_to_vacuum.id,
                'warehouse_id': svl_to_vacuum.warehouse_id.id,
                'location_id': svl_to_vacuum.location_id.id,
                'lot_ids': [(6, 0, line_lot_ids)],
                'line_ids': line_values
            }
            vacuum_svl = self.env['stock.valuation.layer'].sudo()._query_create(vals)

            # Create the account move.
            if self.valuation != 'real_time':
                continue
            vacuum_svl.stock_move_id._account_entry_move(
                vacuum_svl.quantity, vacuum_svl.description, vacuum_svl.id, vacuum_svl.value
            )

            # TODO: FIX THIS
            # Create the related expense entry
            self._create_fifo_vacuum_anglo_saxon_expense_entry(vacuum_svl, svl_to_vacuum)

        # If some negative stock were fixed, we need to recompute the standard price.
        def _check_and_update_avco_cost(product_contexed):
            if not float_is_zero(product_contexed.quantity_svl, precision_rounding=self.uom_id.rounding):
                product_contexed.sudo().with_context(disable_auto_svl=True).standard_price = product_contexed.value_svl / product_contexed.quantity_svl

        product = self.with_company(company.id)
        if product.cost_method == 'average':
            if not is_cost_per_warehouse:
                _check_and_update_avco_cost(product)
            else:
                for warehouse_id in warehouse_ids:
                    product = product.with_context(price_for_warehouse=warehouse_id)
                    _check_and_update_avco_cost(product)
        
        elif product.cost_method == 'fifo':
            if is_cost_per_warehouse:
                for warehouse_id in warehouse_ids:
                    where_clause = [
                        'svl.company_id = %s' % (company.id,),
                        'svl.product_id = %s' % (product.id,),
                        'svl.warehouse_id = %s' % (warehouse_id,),
                        'svll.remaining_qty > 0.0',
                        lot_clause
                    ]

                    where_clause = ' AND '.join(where_clause)
                    
                    self.env.cr.execute("""
                        SELECT
                            svll.remaining_value / svll.remaining_qty AS unit_cost
                        FROM
                            stock_valuation_layer_line svll
                        LEFT JOIN 
                            stock_valuation_layer svl
                            ON (svl.id = svll.svl_id)
                        WHERE
                            {where}
                        ORDER BY
                            svll.id
                        LIMIT
                            1
                    """.format(where=where_clause))
                    candidate = self.env.cr.dictfetchall()

                    new_std_price = 0.0
                    if candidate:
                        new_std_price = candidate[0]['unit_price']
                    product.with_context(
                        price_for_warehouse=warehouse_id,
                        disable_auto_svl=True
                    ).sudo().standard_price = new_std_price
            else:
                where_clause = [
                    'svl.company_id = %s' % (company.id,),
                    'svl.product_id = %s' % (product.id,),
                    'svll.remaining_qty > 0.0',
                    lot_clause
                ]
                where_clause = ' AND '.join(where_clause)
                
                self.env.cr.execute("""
                    SELECT
                        svll.remaining_value / svll.remaining_qty AS unit_cost
                    FROM
                        stock_valuation_layer_line svll
                    LEFT JOIN 
                        stock_valuation_layer svl
                        ON (svl.id = svll.svl_id)
                    WHERE
                        {where}
                    ORDER BY
                        svll.id
                    LIMIT
                        1
                """.format(where=where_clause))
                candidate = self.env.cr.dictfetchall()

                new_std_price = 0.0
                if candidate:
                    new_std_price = candidate[0]['unit_price']
                product.with_context(disable_auto_svl=True).sudo().standard_price = new_std_price

    @api.model
    def _svl_empty_stock_am(self, stock_valuation_layers):
        move_vals_list = super(ProductProduct, self)._svl_empty_stock_am(stock_valuation_layers)
        currency = self.env.company.currency_id
        today = fields.Date.today()
        for move_vals in move_vals_list:
            move_vals.update({
                'date': today,
                'state': 'posted',
                'currency_id': currency.id,
            })
            for line in move_vals.get('line_ids', []):
                line[-1].update({
                    'currency_id': currency.id,
                })
        return move_vals_list

    @api.model
    def _svl_empty_stock_prepare_tmp_move_lines(self, svl_line):
        return {
            'lot_id': svl_line.lot_id.id,
            'qty_done': abs(svl_line.remaining_qty)
        }

    @api.model
    def _svl_empty_stock(self, description, product_category=None, product_template=None):
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        impacted_product_ids = []
        impacted_products = self.env['product.product']
        products_orig_quantity_svl = {}

        # get the impacted products
        domain = [('type', '=', 'product')]
        if product_category is not None:
            domain += [('categ_id', '=', product_category.id)]
        elif product_template is not None:
            domain += [('product_tmpl_id', '=', product_template.id)]
        else:
            raise ValueError()
        products = self.env['product.product'].search_read(domain, ['quantity_svl'])
        for product in products:
            impacted_product_ids.append(product['id'])
        impacted_products |= self.env['product.product'].browse(impacted_product_ids)

        svl_lines = self.env['stock.valuation.layer.line'].search([
            ('product_id', 'in', impacted_products.ids), 
            ('company_id', '=', self.env.company.id),
            ('remaining_qty', '!=', 0.0)
        ])

        # empty out the stock for the impacted products
        empty_stock_svl_list = []
        for product in impacted_products:
            svl_product = svl_lines.filtered(lambda o: o.product_id == product)
            products_orig_quantity_svl[product.id] = {wh.id: {} for wh in svl_product.mapped('warehouse_id')}

            for warehouse in svl_product.mapped('warehouse_id'):
                svl_warehouse = svl_product.filtered(lambda o: o.warehouse_id == warehouse)
                products_orig_quantity_svl[product.id][warehouse.id] = {loc.id: {} for loc in svl_warehouse.mapped('location_id')}

                for location in svl_warehouse.mapped('location_id'):
                    svl_location = svl_warehouse.filtered(lambda o: o.location_id == location)
                    products_orig_quantity_svl[product.id][warehouse.id][location.id] = []

                    move_line_vals_list = []
                    move_line_lot_ids = []
                    for svl_line in svl_location:
                        move_line_vals_list += [(0, 0 , self._svl_empty_stock_prepare_tmp_move_lines(svl_line))]
                        if svl_line.lot_id.id:
                            move_line_lot_ids += [svl_line.lot_id.id]
                    
                    move = self.env['tmp.stock.move'].create({
                        'product_id': product.id,
                        'location_id': location.id,
                        'move_lines': move_line_vals_list
                    })
                    if float_is_zero(move.quantity_done, precision_rounding=product.uom_id.rounding):
                        continue

                    product_contexed = product.with_context(move=move)
                    if is_cost_per_warehouse:
                        product_contexed = product_contexed.with_context(price_for_warehouse=warehouse.id)

                    svl_vals = product_contexed._prepare_out_svl_vals(move.quantity_done, self.env.company)
                    for x, y, line_vals in svl_vals['line_ids']:
                        products_orig_quantity_svl[product.id][warehouse.id][location.id] += [line_vals]

                    svl_vals['description'] = description + svl_vals.pop('rounding_adjustment', '')
                    svl_vals['company_id'] = self.env.company.id
                    svl_vals['warehouse_id'] = warehouse.id
                    svl_vals['location_id'] = location.id
                    svl_vals['lot_ids'] = [(6, 0, move_line_lot_ids)]

                    empty_stock_svl_list.append(svl_vals)
        return empty_stock_svl_list, products_orig_quantity_svl, impacted_products

    def _svl_replenish_stock_am(self, stock_valuation_layers):
        move_vals_list = super(ProductProduct, self)._svl_replenish_stock_am(stock_valuation_layers)
        currency = self.env.company.currency_id
        today = fields.Date.today()
        for move_vals in move_vals_list:
            move_vals.update({
                'date': today,
                'state': 'posted',
                'currency_id': currency.id,
            })
            for line in move_vals.get('line_ids', []):
                line[-1].update({
                    'currency_id': currency.id,
                })
        return move_vals_list

    @api.model
    def _svl_replenish_stock_prepare_tmp_move_lines(self, svl_line_values):
        return {
            'lot_id': svl_line_values['lot_id'],
            'qty_done': abs(svl_line_values['quantity'])
        }

    def _svl_replenish_stock(self, description, products_orig_quantity_svl):
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        refill_stock_svl_list = []
        for product in self:
            product_wise_data = products_orig_quantity_svl[product.id]
            for warehouse_id, warehouse_wise_data in product_wise_data.items():
                for location_id, location_wise_data in warehouse_wise_data.items():

                    move_line_vals_list = []
                    move_line_lot_ids = []
                    for svl_line_values in location_wise_data:
                        move_line_vals_list += [(0, 0, self._svl_replenish_stock_prepare_tmp_move_lines(svl_line_values))]
                        if svl_line_values['lot_id']:
                            move_line_lot_ids += [svl_line_values['lot_id']]

                    move = self.env['tmp.stock.move'].create({
                        'product_id': product.id,
                        'location_id': location_id,
                        'move_lines': move_line_vals_list
                    })
                    if float_is_zero(move.quantity_done, precision_rounding=product.uom_id.rounding):
                        continue

                    product_contexed = product.with_context(move=move)
                    if is_cost_per_warehouse:
                        product_contexed = product_contexed.with_context(price_for_warehouse=warehouse_id)

                    svl_vals = product_contexed._prepare_in_svl_vals(move.quantity_done, product_contexed.standard_price)
                    svl_vals['description'] = description
                    svl_vals['company_id'] = self.env.company.id
                    svl_vals['warehouse_id'] = warehouse_id
                    svl_vals['location_id'] = location_id
                    svl_vals['lot_ids'] = [(6, 0, move_line_lot_ids)]
                    refill_stock_svl_list.append(svl_vals)
        return refill_stock_svl_list


class ProductWarehousePrice(models.Model):
    _name = 'product.warehouse.price'
    _description = 'Product Warehouse Price'

    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    cost_method = fields.Selection(related="product_id.cost_method", readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    standard_price = fields.Float(string='Cost', digits='Product Price')
    has_done_moves = fields.Boolean(compute='_compute_has_done_moves')

    _sql_constraints = [('warehouse_unique', 'unique(company_id,product_id,warehouse_id)', _('Warehouse price already exist!'))]

    def write(self, vals):
        if any(field_name in vals for field_name in self._editable_fields()):
            for record in self:
                if record.has_done_moves:
                    raise ValidationError(_('Cannot edit warehouse costs fields while moves is already done. Please create a new one!'))
        if 'standard_price' in vals and not self.env.context.get('disable_auto_svl'):
            for record in self:
                record.product_id.with_context(price_for_warehouse=record.warehouse_id.id).filtered(lambda p: p.cost_method != 'fifo')._change_standard_price(vals['standard_price'])
        return super(ProductWarehousePrice, self).write(vals)

    def unlink(self):
        if not self.env.context.get('disable_auto_svl', False):
            for record in self:
                if record.has_done_moves:
                    raise ValidationError(_('Cannot delete warehouse costs while moves is already done!'))
                record.product_id.with_context(price_for_warehouse=record.warehouse_id.id).filtered(lambda p: p.cost_method != 'fifo')._change_standard_price(0.0)
        return super(ProductWarehousePrice, self).unlink()

    @api.model
    def _editable_fields(self):
        return ['company_id', 'product_id', 'warehouse_id']

    @api.depends('company_id', 'product_id', 'warehouse_id')
    def _compute_has_done_moves(self):
        Move = self.env['stock.move'].sudo()
        for record in self:
            view_location_id = record.warehouse_id.view_location_id.id
            done_moves = Move.search([
                ('company_id', '=', record.company_id.id),
                ('product_id', '=', record.product_id.id),
                ('state', '=', 'done'),
                '|',
                    ('location_id', 'child_of', view_location_id),
                    ('location_dest_id', 'child_of', view_location_id)
            ])
            record.has_done_moves = len(done_moves) > 0


class TmpStockMove(models.TransientModel):
    _name = 'tmp.stock.move'
    _description = 'Temporary Stock Move'

    product_id = fields.Many2one('product.product', required=True)
    move_lines = fields.One2many('tmp.stock.move.line', 'move_id')
    inventory_id = fields.Boolean()
    quantity_done = fields.Float(compute='_compute_quantity_done')
    location_id = fields.Many2one('stock.location')

    @api.depends('move_lines', 'move_lines.qty_done')
    def _compute_quantity_done(self):
        for record in self:
            record.quantity_done = sum(line.qty_done for line in record.move_lines)

    def _get_valued_move_lines(self):
        return self.move_lines

    def _get_out_move_lines(self):
        return self.move_lines

    def _get_in_move_lines(self):
        return self.move_lines

    def _ordered_lots(self):
        lot_ids = []
        for move_line in self.move_lines:
            lot_id = move_line.lot_id.id
            if lot_id not in lot_ids:
                lot_ids += [lot_id]
        return lot_ids

    def _get_lot_move_lines_dict(self):
        move_lines = self.move_lines
        lot_dict = {}
        for move_line in move_lines:
            lot_id = move_line.lot_id.id
            if lot_id not in lot_dict:
                lot_dict[lot_id] = [move_line.id]
            else:
                lot_dict[lot_id] += [move_line.id]
        return lot_dict

    def _warehouse_id(self):
        self.ensure_one()
        return self.location_id.get_warehouse().id

    def _location_id(self):
        self.ensure_one()
        return self.location_id.id


class TmpStockMoveLine(models.TransientModel):
    _name = 'tmp.stock.move.line'
    _description = 'Temporary Stock Move Line'

    move_id = fields.Many2one('tmp.stock.move', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', related='move_id.product_id')
    product_uom_id = fields.Many2one('uom.uom', related='product_id.uom_id')
    lot_id = fields.Many2one('stock.production.lot')
    qty_done = fields.Float()

    def _prepare_in_svl_vals(self, quantity, unit_cost):
        self.ensure_one()

        value = quantity * unit_cost
        values = {
            'lot_id': self.lot_id.id,
            'quantity': quantity,
            'unit_cost': unit_cost,
            'value': value
        }
        if self.product_id.cost_method in ('average', 'fifo'):
            values.update({
                'remaining_qty': quantity,
                'remaining_value': value
            })
        return values

    def _prepare_out_svl_vals(self, quantity, fifo_vals):
        self.ensure_one()

        factor = -1 if quantity > 0 else 1
        values = {
            'lot_id': self.lot_id.id,
            'quantity': factor * quantity,
            'unit_cost': fifo_vals['unit_cost'],
            'value': factor * quantity * fifo_vals['unit_cost']
        }
        if quantity < 0.0:
            values.update({
                'remaining_qty': values['quantity'],
                'remaining_value': values['value']
            })
        return values
