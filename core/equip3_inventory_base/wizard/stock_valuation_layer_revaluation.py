from odoo import models, fields, api, _
from odoo.tools import float_is_zero, misc


class StockValuationLayerRevaluation(models.TransientModel):
    _inherit = 'stock.valuation.layer.revaluation'

    @api.model
    def _is_cost_per_warehouse(self):
        return eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

    product_tracking = fields.Selection(related='product_id.tracking')
    lot_id = fields.Many2one('stock.production.lot', string='Lot/Serial Number')
    is_cost_per_warehouse = fields.Boolean(default=_is_cost_per_warehouse)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')

    current_value_svl = fields.Float(related=None, compute='_compute_svl')
    current_quantity_svl = fields.Float(related=None, compute='_compute_svl')

    current_value_message = fields.Text(compute='_compute_message')
    new_value_message = fields.Text(compute='_compute_message')

    @api.depends('lot_id', 'is_cost_per_warehouse', 'warehouse_id')
    def _compute_svl(self):
        is_cost_per_warehouse = self._is_cost_per_warehouse()
        for record in self:
            product = record.product_id.with_context(lot_id=record.lot_id.id)
            if is_cost_per_warehouse:
                product = product.with_context(price_for_warehouse=record.warehouse_id.id)
            record.current_value_svl = product.value_svl
            record.current_quantity_svl = product.quantity_svl

    @api.depends('product_id', 'lot_id', 'product_uom_name', 'company_id', 'currency_id', 'added_value', 'warehouse_id')
    def _compute_message(self):
        env = self.env
        for record in self:
            lot = record.lot_id
            product = record.product_id.with_context(lot_id=lot.id)
            added_value = record.added_value
            product_uom_name = record.product_uom_name
            currency_id = record.currency_id
            warehouse = record.warehouse_id

            if warehouse:
                warehouses = warehouse
            else:
                warehouses = self.env['stock.valuation.layer.line'].search([
                    ('product_id', '=', product.id),
                    ('remaining_qty', '>', 0),
                    ('company_id', '=', record.company_id.id),
                    ('lot_id', '=', lot.id)
                ]).mapped('warehouse_id')

            current_message = []
            new_message = []
            for warehouse in warehouses:
                product = product.with_context(price_for_warehouse=warehouse.id)
                quantity_svl = product.quantity_svl
                value_svl = 0.0
                if float_is_zero(quantity_svl, precision_rounding=product.uom_id.rounding):
                    new_value_by_qty = value_svl = 0.0
                else:
                    value_svl = product.value_svl
                    new_value = value_svl + added_value
                    new_value_by_qty = new_value / product.quantity_svl
                current_message += ['- %s: %s for %s %s' % (warehouse.display_name, misc.formatLang(env, value_svl, currency_obj=currency_id), quantity_svl, product_uom_name)]
                new_message += ['- %s = %s (%s by %s)' % (warehouse.display_name, misc.formatLang(env, new_value, currency_obj=currency_id), misc.formatLang(env, new_value_by_qty, currency_obj=currency_id), product_uom_name)]
            
            record.current_value_message = '\n'.join(current_message)
            record.new_value_message = '\n'.join(new_message)

    def action_validate_revaluation(self):
        """ Revaluate the stock for `self.product_id` in `self.company_id`.

        - Change the stardard price with the new valuation by product unit.
        - Create a manual stock valuation layer with the `added_value` of `self`.
        - Distribute the `added_value` on the remaining_value of layers still in stock (with a remaining quantity)
        - If the Inventory Valuation of the product category is automated, create
        related account move.
        """
        self.ensure_one()
        if self.currency_id.is_zero(self.added_value):
            raise UserError(_("The added value doesn't have any impact on the stock valuation"))

        product_id = self.product_id.with_company(self.company_id)
        domain = [
            ('product_id', '=', product_id.id),
            ('remaining_qty', '>', 0),
            ('company_id', '=', self.company_id.id),
            ('lot_id', '=', self.lot_id.id)
        ]
        if self.is_cost_per_warehouse:
            domain += [('warehouse_id', '=', self.warehouse_id.id)]

        remaining_svls = self.env['stock.valuation.layer.line'].search(domain)

        # Create a manual stock valuation layer
        if self.reason:
            description = _("Manual Stock Valuation: %s.", self.reason)
        else:
            description = _("Manual Stock Valuation: No Reason Given.")

        added_value = self.added_value
        company_id = self.company_id
        currency_id = self.currency_id

        date = self.date
        property_valuation = self.property_valuation
        account_id = self.account_id
        account_journal_id = self.account_journal_id

        move_vals_list = []
        for warehouse in remaining_svls.mapped('warehouse_id'):
            product_id = product_id.with_context(price_for_warehouse=warehouse.id)
            warehouse_remaining_svls = remaining_svls.filtered(lambda o: o.warehouse_id == warehouse)

            for location in warehouse_remaining_svls.mapped('location_id'):
                product_id = product_id.with_context(price_for_location=location.id)
                location_remaining_svls = warehouse_remaining_svls.filtered(lambda o: o.warehouse_id == warehouse)

                for svl_line in location_remaining_svls:
                    lot_id = svl_line.lot_id.id
                    product_id = product_id.with_context(lot_id=lot_id)

                    product_value_svl = product_id.value_svl
                    product_quantity_svl = product_id.quantity_svl
                    product_new_value_svl = product_value_svl + added_value
                    product_new_value_svl_by_qty = product_new_value_svl / product_quantity_svl

                    if product_id.categ_id.property_cost_method == 'average':
                        description += _(
                            " Product cost updated from %(previous)s to %(new_cost)s.",
                            previous=product_id.standard_price,
                            new_cost=product_id.standard_price + added_value / product_quantity_svl
                        )

                    revaluation_svl_vals = {
                        'company_id': company_id.id,
                        'product_id': product_id.id,
                        'description': description,
                        'value': added_value,
                        'quantity': 0,
                        'warehouse_id': warehouse.id,
                        'location_id': location.id,
                        'lot_ids': [(6, 0, [lot_id] if lot_id else [])],
                        'line_ids': [(0, 0, {
                            'quantity': 0,
                            'value': added_value,
                            'lot_id': lot_id
                        })]
                    }

                    svl_line_unit_cost = svl_line.remaining_value / svl_line.remaining_qty
                    diff_unit_cost = product_new_value_svl_by_qty - svl_line_unit_cost
                    value_add_to_remaining = diff_unit_cost * svl_line.remaining_qty
                    svl_line.remaining_value += value_add_to_remaining
                    svl_line.svl_id.remaining_value += value_add_to_remaining

                    revaluation_svl = self.env['stock.valuation.layer']._query_create(revaluation_svl_vals)

                    # Update the stardard price in case of AVCO
                    if product_id.categ_id.property_cost_method == 'average':
                        product_id.with_context(disable_auto_svl=True).standard_price += added_value / product_quantity_svl

                    # If the Inventory Valuation of the product category is automated, create related account move.
                    if property_valuation != 'real_time':
                        return True

                    accounts = product_id.product_tmpl_id.get_product_accounts()

                    if added_value < 0:
                        debit_account_id = account_id.id
                        credit_account_id = accounts.get('stock_valuation') and accounts['stock_valuation'].id
                    else:
                        debit_account_id = accounts.get('stock_valuation') and accounts['stock_valuation'].id
                        credit_account_id = account_id.id

                    move_vals = {
                        'journal_id': account_journal_id.id or accounts['stock_journal'].id,
                        'company_id': company_id.id,
                        'ref': _("Revaluation of %s", product_id.display_name),
                        'stock_valuation_layer_ids': [(6, None, [revaluation_svl.id])],
                        'date': date or fields.Date.today(),
                        'move_type': 'entry',
                        'line_ids': [(0, 0, {
                            'name': _('%(user)s changed stock valuation from  %(previous)s to %(new_value)s - %(product)s',
                                user=self.env.user.name,
                                previous=product_value_svl,
                                new_value=product_value_svl + added_value,
                                product=product_id.display_name,
                            ),
                            'account_id': debit_account_id,
                            'debit': abs(added_value),
                            'credit': 0,
                            'product_id': product_id.id,
                        }), (0, 0, {
                            'name': _('%(user)s changed stock valuation from  %(previous)s to %(new_value)s - %(product)s',
                                user=self.env.user.name,
                                previous=product_value_svl,
                                new_value=product_value_svl + added_value,
                                product=product_id.display_name,
                            ),
                            'account_id': credit_account_id,
                            'debit': 0,
                            'credit': abs(added_value),
                            'product_id': product_id.id,
                        })],
                    }
                    move_vals_list += [move_vals]

        if move_vals_list:
            self.env['account.move']._query_create(move_vals_list)

        return True
