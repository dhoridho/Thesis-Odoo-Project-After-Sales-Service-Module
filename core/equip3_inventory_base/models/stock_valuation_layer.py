import logging
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, tools, _
from odoo.tools import float_is_zero
from odoo.addons.base.models.ir_model import quote
from odoo.exceptions import ValidationError, UserError
from collections import defaultdict

_logger = logging.getLogger(__name__)


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    line_ids = fields.One2many('stock.valuation.layer.line', 'svl_id', string='Lines', readonly=True)

    lot_ids = fields.Many2many('stock.production.lot', string='Lot/Serial Numbers', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', readonly=True)
    location_id = fields.Many2one('stock.location', string='Location', readonly=True)
    inventory_id = fields.Many2one('stock.inventory', string='Inventory', readonly=True)

    # technical fields
    is_repaired = fields.Boolean()

    # @api.constrains('currency_id', 'value', 'line_ids', 'line_ids.value')
    # def _check_value(self):x
    #     for record in self:
    #         currency = record.currency_id
    #         if record.line_ids and not currency.is_zero(record.value - sum(record.line_ids.mapped('value'))):
    #             raise ValidationError(_('The value in the valuation layer must be the same as the sum of the values ​​in the valuation layer lines!'))

    def _ordered_lots(self):
        lot_ids = []
        for svl in self:
            for lot_id in svl.stock_move_id._ordered_lots():
                if lot_id not in lot_ids:
                    lot_ids += [lot_id]
        return lot_ids

    def _get_stock_accounts(self):
        self.ensure_one()
        product = self.product_id
        accounts = product.product_tmpl_id.get_product_accounts()

        journal = accounts['stock_journal']
        if not journal:
            raise UserError(_('Please set stock journal for product %s' % product.display_name))

        stock_valuation_id = accounts.get('stock_valuation') and accounts['stock_valuation'].id
        if not stock_valuation_id:
            raise UserError(_('Please set stock valuation account for product %s' % product.display_name))

        stock_output_id = accounts['stock_output'].id
        if not stock_output_id:
            raise UserError(_('Please set stock output account for product %s' % product.display_name))

        stock_input_id = accounts['stock_output'].id
        if not stock_input_id:
            raise UserError(_('Please set stock input account for product %s' % product.display_name))

        if self.value < 0:
            return journal.id, stock_output_id, stock_valuation_id
        return journal.id, stock_valuation_id, stock_input_id

    def _fifo_revaluate(self):
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        company = self and self[0].company_id or self.env.company

        groupby = ['product_id']
        if is_cost_per_warehouse:
            groupby += ['warehouse_id']
        
        svl_dict = self.mapped('product_id')._query_svl(company, groupby=groupby)
        
        account_move_vals_list = []
        for svl in self:
            svl_lot_ids = svl.lot_ids

            remaining_svl_lines = self.env['stock.valuation.layer.line'].search([
                ('company_id', '=', svl.company_id.id),
                ('product_id', '=', svl.product_id.id),
                ('warehouse_id', '=', svl.warehouse_id.id),
                ('location_id', '=', svl.location_id.id),
                ('lot_id', 'in', svl_lot_ids.ids or [False]),
                ('remaining_qty', '>', 0)
            ])

            line_values = {}
            for svl_line in svl.line_ids:
                line_values[svl_line.lot_id.id] = {'value': svl_line.value, 'unit_cost': svl_line.unit_cost}
            svl.line_ids.write({'unit_cost': 0.0})

            svl_rem_vals_dict = defaultdict(lambda: 0.0)
            svl_line_dict = {}
            for svl_line in remaining_svl_lines:
                old_unit_cost = svl_line.remaining_value / svl_line.remaining_qty
                diff_unit_cost = line_values[svl_line.lot_id.id]['unit_cost'] - old_unit_cost
                value_add_to_remaining = diff_unit_cost * svl_line.remaining_qty

                remaining_value = svl_line.remaining_value + value_add_to_remaining
                svl_line.write({
                    'remaining_value': remaining_value
                })
                svl_line_dict[svl_line.id] = svl_line.remaining_value
                svl_rem_vals_dict[svl_line.svl_id] += value_add_to_remaining
                
            for svl_rem, extra_value in svl_rem_vals_dict.items():
                svl_rem.remaining_value += extra_value

            if svl.product_id.cost_method == 'fifo':
                where = [
                    'svl.product_id = %s' % svl.product_id.id,
                    'svl.company_id = %s' % svl.company_id.id,
                    'svll.remaining_qty > 0.0',
                ]
                if svl_lot_ids:
                    if len(svl_lot_ids) == 1:
                        where += ['svll.lot_id = %s' % svl_lot_ids[0].id]
                    else:
                        where += ['svll.lot_id IN %s' % (tuple(svl_lot_ids.ids),)]

                if is_cost_per_warehouse:
                    where += ['svl.warehouse_id = %s' % svl.warehouse_id.id]
                where = ' AND '.join(where)

                self._cr.execute("""
                    SELECT
                        svll.id,
                        svll.remaining_value,
                        svll.remaining_qty
                    FROM
                        stock_valuation_layer_line svll
                    LEFT JOIN
                        stock_valuation_layer svl
                        ON (svl.id = svll.svl_id)
                    WHERE
                        {where}
                    ORDER BY
                        svll.create_date
                    LIMIT
                        1
                """.format(where=where))

                candidates = self._cr.dictfetchall()
                
                if candidates:
                    remaining_value = svl_line_dict.get(candidates[0]['id'], candidates[0]['remaining_value'])
                    new_standard_price = remaining_value / candidates[0]['remaining_qty']
                    product = svl.product_id.with_context(disable_auto_svl=True)
                    if is_cost_per_warehouse:
                        product = product.with_context(price_for_warehouse=svl.warehouse_id.id)
                    product.with_context(disable_auto_svl=True).standard_price = new_standard_price

            elif svl.product_id.cost_method == 'average':
                product = svl.product_id.with_context(disable_auto_svl=True)
                key = product.id
                if is_cost_per_warehouse:
                    key = (key, svl.warehouse_id.id)
                    product = product.with_context(price_for_warehouse=svl.warehouse_id.id)

                vals_svl_dict = svl_dict.get(key, {})
                quantity_svl = vals_svl_dict.get('quantity', 0.0)
                if not float_is_zero(quantity_svl, precision_rounding=product.uom_id.rounding):
                    product.standard_price = vals_svl_dict.get('value', 0.0) / quantity_svl

            # prepare journal entries
            account_move_vals_list  += [svl._fifo_revaluate_prepare_account_move_vals()]

        if account_move_vals_list:
            self.env['account.move']._query_create(account_move_vals_list)

    def _fifo_revaluate_prepare_account_move_vals(self):
        self.ensure_one()
        journal_id, debit_account_id, credit_account_id = self._get_stock_accounts()
        return {
            'name': self.env['account.journal'].browse(journal_id).sequence_id.next_by_id(),
            'journal_id': journal_id,
            'company_id': self.company_id.id,
            'ref': self.description,
            'stock_valuation_layer_ids': [(6, None, [self.id])],
            'date': fields.Date.today(),
            'move_type': 'entry',
            'inventory_id': self.inventory_id.id,
            'state': 'posted',
            'currency_id': self.company_id.currency_id.id,
            'line_ids': [(0, 0, {
                'name': self.description,
                'account_id': debit_account_id,
                'debit': abs(self.value),
                'credit': 0,
                'product_id': self.product_id.id,
                'currency_id': self.company_id.currency_id.id
            }), (0, 0, {
                'name': self.description,
                'account_id': credit_account_id,
                'debit': 0,
                'credit': abs(self.value),
                'product_id': self.product_id.id,
                'currency_id': self.company_id.currency_id.id
            })],
        }

    def _change_standard_price_prepare_account_move_vals(self, new_price):
        self.ensure_one()

        product = self.product_id
        standard_price = product.with_context(price_for_warehouse=self.warehouse_id.id).standard_price
        accounts = product.product_tmpl_id.get_product_accounts()

        # Sanity check.
        if not accounts.get('stock_journal'):
            raise UserError(_('Please set stock journal for product %s' % product.display_name))
        if not accounts.get('expense'):
            raise UserError(_('You must set a counterpart account on your product category.'))
        if not accounts.get('stock_valuation'):
            raise UserError(_('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))

        journal = accounts['stock_journal']

        value = self.value
        if value < 0:
            debit_account_id = accounts['expense'].id
            credit_account_id = accounts['stock_valuation'].id
        else:
            debit_account_id = accounts['stock_valuation'].id
            credit_account_id = accounts['expense'].id

        ref = product.display_name
        line_name = _('%(user)s changed cost from %(previous)s to %(new_price)s - %(product)s',
            user=self.env.user.name,
            previous=standard_price,
            new_price=new_price,
            product=product.display_name)
        
        inventory = self.env['stock.inventory'].browse(self.env.context.get('inventory_id', False))
        if inventory.exists():
            ref = _('INV:') + (inventory.display_name or '')
            ref = '%s - %s' % (ref, product.name)
            line_name = ref
        elif self.env.context.get('is_product_price_update', False):
            line_name = _('Product value automatically modified')
        
        return {
            'name': journal.sequence_id.next_by_id(),
            'journal_id': journal.id,
            'company_id': self.company_id.id,
            'ref': ref,
            'stock_valuation_layer_ids': [(6, None, [self.id])],
            'date': fields.Date.today(),
            'move_type': 'entry',
            'inventory_id': inventory.id,
            'state': 'posted',
            'currency_id': self.company_id.currency_id.id,
            'line_ids': [(0, 0, {
                'name': line_name,
                'account_id': debit_account_id,
                'debit': abs(value),
                'credit': 0,
                'product_id': product.id,
                'currency_id': self.company_id.currency_id.id
            }), (0, 0, {
                'name': line_name,
                'account_id': credit_account_id,
                'debit': 0,
                'credit': abs(value),
                'product_id': product.id,
                'currency_id': self.company_id.currency_id.id
            })],
        }

    @api.model
    def _create_repair_cron(self):
        if not self.env.context.get('bypass_check', False):
            repair_cron = self.env['ir.cron'].search([('active', '=', True), ('name', '=', _('Repair Valuation Lines'))])
            if repair_cron.exists():
                raise ValidationError(_('Repair cron is running!'))
        
        self.env['ir.cron'].create({
            'name': _('Repair Valuation Lines'),
            'model_id': self.env.ref('stock_account.model_stock_valuation_layer').id,
            'state': 'code',
            'code': 'model._repair_valuation_lines_batch()',
            'user_id': self.env.ref('base.user_root').id,
            'numbercall': 1,
            'interval_type': 'days',
            'interval_number': 1,
            'doall': False,
            'nextcall': fields.Datetime.now()
        })

        if not self.env.context.get('bypass_check', False):
            self.env['bus.bus'].sendone(
                (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                {'type': 'simple_notification', 'title': _('Action Repair'), 'message': _('Repair cron will running immediately.'), 'sticky': False, 'warning': True}
            )

    @api.model
    def _repair_valuation_lines_batch(self, batch=500):
        svls = self.sudo().search([('line_ids', '=', False), ('is_repaired', '=', False)], limit=batch)
        _logger.info('Processing %s stock valuation layers' % len(svls))
        if svls:
            svls._repair_valuation_lines()
            self.with_context(bypass_check=True)._create_repair_cron()
        else:
            self.env['ir.cron'].search([('active', '=', False), ('name', '=', _('Repair Valuation Lines'))]).unlink()

    def _repair_valuation_lines(self):
        for i, svl in enumerate(self):
            _logger.info('>> %s: %s/%s' % (svl.id, i + 1, len(self)))
            
            svl_move = svl.stock_move_id
            line_values_generator = []

            if svl_move:
                if svl_move._is_in():
                    line_values_generator = svl._repair_in_valuation_lines()
                elif svl_move._is_out():
                    line_values_generator = svl._repair_out_valuation_lines()
                elif svl_move.move_line_ids:
                    # unknown moves, treat like `in` and `out` moves based quantity
                    if svl.quantity >= 0:
                        line_values_generator = svl._repair_in_valuation_lines(forced_move_lines=svl_move.move_line_ids)
                    else:
                        line_values_generator = svl._repair_out_valuation_lines(forced_move_lines=svl_move.move_line_ids)
                else:
                    line_values_generator = svl._repair_nomove_valuation_lines()

                warehouse_id = svl_move._warehouse_id()
                location_id = svl_move._location_id()
            else:
                line_values_generator = svl._repair_nomove_valuation_lines()
                warehouse_id = False
                location_id = False
            
            # warehouse & location
            query = """
            UPDATE
                stock_valuation_layer
            SET
                is_repaired = True,
                warehouse_id = %s,
                location_id = %s
            WHERE
                id = %s
            """
            self.env.cr.execute(query, [
                warehouse_id or None,
                location_id or None,
                svl.id
            ])

            # lot_ids
            self.env.cr.execute("DELETE FROM stock_production_lot_stock_valuation_layer_rel WHERE stock_valuation_layer_id = %s", [svl.id])
            for lot in svl_move.lot_ids:
                query = """
                INSERT INTO 
                    stock_production_lot_stock_valuation_layer_rel (stock_valuation_layer_id, stock_production_lot_id) 
                VALUES %s"""
                self.env.cr.execute(query, [(svl.id, lot.id)])

            # line_ids
            self.env.cr.execute("DELETE FROM stock_valuation_layer_line WHERE svl_id = %s", [svl.id])
            for values in line_values_generator:
                query = """
                INSERT INTO
                    stock_valuation_layer_line ({cols}) 
                VALUES %s""".format(
                    cols=", ".join(quote(fname) for fname in ('svl_id', 'lot_id', 'quantity', 'unit_cost', 'value', 'remaining_qty', 'remaining_value')))
                self.env.cr.execute(query, [(
                    svl.id,
                    values['lot_id'] or None,
                    values['quantity'],
                    values['unit_cost'],
                    values['value'],
                    values.get('remaining_qty', 0.0),
                    values.get('remaining_value', 0.0),
                )])
        self.env.cr.commit()

    def _repair_in_valuation_lines(self, forced_move_lines=None):
        self.ensure_one()
        raise ValidationError(_('Not supported yet!'))

        move = self.stock_move_id
        unit_cost = self.unit_cost
        product = self.product_id
        qty_to_take = self.quantity - self.remaining_qty
        lines = move._get_lot_move_lines_dict(forced_move_lines=forced_move_lines)

        for lot_id in move._ordered_lots():
            lot_move_lines = self.env['stock.move.line'].browse(lines[lot_id])
            values = move._prepare_line_in_svl_vals(lot_id, lot_move_lines, unit_cost)

            if product.cost_method in ('average', 'fifo') and qty_to_take > 0:
                remaining_qty = values.get('remaining_qty', 0.0)
                qty_taken = min(qty_to_take, remaining_qty)
                values.update({
                    'remaining_qty': remaining_qty - qty_taken,
                    'remaining_value': (remaining_qty - qty_taken) * unit_cost
                })
                qty_to_take -= qty_taken
            yield values

    def _repair_out_valuation_lines(self, forced_move_lines=None):
        self.ensure_one()
        raise ValidationError(_('Not supported yet!'))

        move = self.stock_move_id
        unit_cost = self.unit_cost
        product = self.product_id
        satisfied_qty = abs(self.quantity - self.remaining_qty)
        lines = move._get_lot_move_lines_dict(forced_move_lines=forced_move_lines)

        current_qty = 0.0
        for lot_id in move._ordered_lots():
            lot_move_lines = self.env['stock.move.line'].browse(lines[lot_id])
            values = move._prepare_line_out_svl_vals(lot_id, lot_move_lines, unit_cost, {})

            quantity = abs(values.get('quantity', 0.0))
            current_qty += quantity
            if product.cost_method in ('average', 'fifo') and current_qty > satisfied_qty:
                qty_taken = min(current_qty - satisfied_qty, quantity)
                values.update({
                    'remaining_qty': -qty_taken,
                    'remaining_value': -qty_taken * unit_cost
                })
            yield values

    def _repair_nomove_valuation_lines(self):
        self.ensure_one()
        yield {
            'lot_id': False,
            'quantity': self.quantity,
            'unit_cost': self.unit_cost,
            'value': self.value,
            'remaining_qty': self.remaining_qty,
            'remaining_value': self.remaining_value
        }


class StockValuationLayerLine(models.Model):
    _name = 'stock.valuation.layer.line'
    _description = 'Valuation Line'

    @api.model
    def create(self, vals):
        if 'description' not in vals and 'svl_id' in vals:
            vals['description'] = self.env['stock.valuation.layer'].browse(vals['svl_id']).description
        return super(StockValuationLayerLine, self).create(vals)

    svl_id = fields.Many2one('stock.valuation.layer', required=True, ondelete='cascade', delegate=True, string='Valuation')
    lot_id = fields.Many2one('stock.production.lot', string='Lot/Serial Number', readonly=True)
    quantity = fields.Float('Quantity', digits=0, help='Quantity', readonly=True)
    unit_cost = fields.Monetary('Unit Value', readonly=True)
    value = fields.Monetary('Total Value', readonly=True)
    remaining_qty = fields.Float(digits=0, readonly=True)
    remaining_value = fields.Monetary('Remaining Value', readonly=True)
    description = fields.Char('Description', readonly=True)
    rounding_error = fields.Monetary()
    stock_move_line_id = fields.Many2one('stock.move.line', 'Stock Move Line', readonly=True, check_company=True, index=True)

    def _ordered_lots(self):
        lot_ids = []
        for line in self:
            lot_id = line.lot_id.id
            if lot_id not in lot_ids:
                lot_ids += [lot_id]
        return lot_ids

    def _prepare_candidate_values(self, quantity=0.0):
        self.ensure_one()
        unit_cost = self.remaining_value / self.remaining_qty
        return {
            'stock_move_line_id': self.stock_move_line_id.id,
            'lot_id': self.lot_id.id,
            'unit_cost': unit_cost,
            'quantity': quantity,
            'value': quantity * unit_cost
        }