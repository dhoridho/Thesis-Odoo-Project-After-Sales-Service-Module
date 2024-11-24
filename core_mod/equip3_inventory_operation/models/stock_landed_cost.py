
from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError
from datetime import datetime, date, timedelta
import json
from collections import defaultdict
from odoo.tools.float_utils import float_is_zero
from odoo.exceptions import UserError
from lxml import etree



class StockLandedCost(models.Model):
    _inherit = "stock.landed.cost"

    # domain_field = fields.Char(compute="_compute_domain_field")
    picking_type_id = fields.Selection([
        ('incoming', 'Incoming'),
        ('outgoing', 'Outgoing')
    ], string="Operation",
        required=True,
        default="incoming")

    vendor_bill = fields.Selection([
        ('create_bill', 'Create Bill'),
        ('draft_bill', 'Choose Draft Bill')
    ], string="Vendor Bill Creation",
        required=True,
        default="create_bill")
    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')
    product_cost_lines = fields.One2many(comodel_name='product.cost.lines', inverse_name='cost_id',
                                         string='Product Cost Lines', copy=True, states={'done': [('readonly', True)]})
    picking_ids_domain = fields.Char(string='Domain Pickings', compute='_compute_picking_ids_domain')

    cost_lines_no_create = fields.One2many('stock.landed.cost.lines', related='cost_lines', readonly=False)

    vendor_bill_id = fields.Many2one('account.move', domain=[('move_type', '=', 'in_invoice'), ('state', '=', 'draft')])
    account_move_ids = fields.Many2many('account.move', string='Vendor Bills', readonly=True)

    def _check_sum(self):
        # override
        return True
    
    @api.depends('from_date', 'to_date')
    def _compute_picking_ids_domain(self):
        StockPicking = self.env['stock.picking'].sudo()
        for rec in self:
            domain = [('date_done', '>=', rec.from_date), ('date_done', '<=', rec.to_date), ('state', '=', 'done')]
            picking_data = StockPicking.search_read(domain, ['id'])
            picking_ids = [data['id'] for data in picking_data]
            rec.picking_ids_domain = json.dumps([('id', 'in', picking_ids)])

    # @api.depends('company_id')
    # def _compute_allowed_picking_ids(self):
    #     valued_picking_ids_per_company = defaultdict(list)
    #     if self.company_id:
    #         self.env.cr.execute("""SELECT sm.picking_id, sm.company_id
    #                                  FROM stock_move AS sm
    #                            INNER JOIN stock_valuation_layer AS svl ON svl.stock_move_id = sm.id
    #                                 WHERE sm.picking_id IS NOT NULL AND sm.company_id IN %s
    #                              GROUP BY sm.picking_id, sm.company_id""", [tuple(self.company_id.ids)])
    #         for res in self.env.cr.fetchall():
    #             valued_picking_ids_per_company[res[1]].append(res[0])
    #     for cost in self:
    #         cost.allowed_picking_ids = valued_picking_ids_per_company[cost.company_id.id]

    @api.depends('company_id', 'picking_type_id')
    def _compute_allowed_picking_ids(self):
        valued_picking_ids_per_company = defaultdict(list)
        branch_ids = self.env.user.branch_ids.ids
        if self.company_id:
            if self.picking_type_id == 'incoming':
                internal = '%INT/IN%'
                self.env.cr.execute("""SELECT sm.picking_id, sm.company_id
                                        FROM stock_move AS sm
                                INNER JOIN stock_valuation_layer AS svl ON svl.stock_move_id = sm.id
                                LEFT JOIN stock_picking_type AS spt on sm.picking_type_id = spt.id
                                        WHERE sm.picking_id IS NOT NULL AND sm.company_id IN %s AND spt.code = %s or sm.reference like %s and sm.branch_id in %s
                                    GROUP BY sm.picking_id, sm.company_id""", [tuple(self.company_id.ids), self.picking_type_id, internal, tuple(branch_ids)])
            if self.picking_type_id == 'outgoing':
                internal = '%INT/OUT%'
                self.env.cr.execute("""SELECT sm.picking_id, sm.company_id
                                        FROM stock_move AS sm
                                INNER JOIN stock_valuation_layer AS svl ON svl.stock_move_id = sm.id
                                LEFT JOIN stock_picking_type AS spt on sm.picking_type_id = spt.id
                                        WHERE sm.picking_id IS NOT NULL AND sm.company_id IN %s AND spt.code = %s or sm.reference like %s and sm.branch_id IN %s
                                    GROUP BY sm.picking_id, sm.company_id""", [tuple(self.company_id.ids), self.picking_type_id, internal, tuple(branch_ids)])
            for res in self.env.cr.fetchall():
                valued_picking_ids_per_company[res[1]].append(res[0])
        for cost in self:
            # cost.allowed_picking_ids = valued_picking_ids_per_company[cost.company_id.id]
            picking_ids = self.env['stock.picking'].search(
                [('id', 'in', valued_picking_ids_per_company[cost.company_id.id])])
            picking_ids = [pick.id for pick in picking_ids.filtered(
                lambda x: x.branch_id)]
            cost.allowed_picking_ids = picking_ids

    @api.onchange('picking_ids', 'cost_lines')
    def _onchange_set_product_cost_lines(self):
        values = [(5,)]
        for line_values in self._get_product_cost_lines():
            values += [(0, 0, line_values)]
        self.product_cost_lines = values

    def _get_product_cost_lines(self):
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        values = []
        pickings = self.picking_ids.filtered(
            lambda o: len(o.move_ids_without_package.filtered(
                lambda m: m.product_id.cost_method in ('average', 'fifo'))) > 0)
        cost_lines = self.cost_lines
        currency = self.company_id.currency_id
        prec_digits = self.company_id.currency_id.decimal_places

        if not pickings or not cost_lines:
            return values

        n_transfers = len(pickings)
        picking_moves_dict = {}
        svls = self.env['stock.valuation.layer']
        for picking in pickings:
            picking_id = picking.id or picking._origin.id
            moves = picking.move_ids_without_package.filtered(lambda o: o.product_id.cost_method in ('average', 'fifo'))
            picking_moves_dict[picking_id] = moves
            svls |= moves.stock_valuation_layer_ids
        
        total_quantity = 0.0
        if any(line.split_method_lite == 'by_quantity' for line in cost_lines):
            total_quantity = sum(svls.mapped('quantity'))

        factors = {}
        if any(line.split_method_lite == 'by_current_cost_price' for line in cost_lines):
            for move in svls.mapped('stock_move_id'):
                move_id = move.id or move._origin.id
                svl_move = move.stock_valuation_layer_ids
                unit_cost = 0.0
                if svl_move:
                    unit_cost = sum(svl_move.mapped('unit_cost')) / len(svl_move)
                factors[move_id] = unit_cost

        total_unit_cost = sum(factors.values())
        if total_unit_cost:
            for move_id, unit_cost in factors.items():
                factors[move_id] /= total_unit_cost

        new_costs = {}
        for cost_line in cost_lines:
            cost_line_id = cost_line.id or cost_line._origin.id
            split_method = cost_line.split_method_lite
            extra_cost = cost_line.price_unit

            cost_per_picking = 0.0
            if split_method == 'equal' and n_transfers:
                cost_per_picking = extra_cost / n_transfers

            cost_per_qty = 0.0
            if split_method == 'by_quantity' and total_quantity:
                cost_per_qty = extra_cost / total_quantity

            for picking in pickings:
                picking_id = picking.id or picking._origin.id
                picking_moves = picking_moves_dict[picking_id]

                n_moves = len(picking_moves)
                cost_per_move = cost_per_picking / n_moves

                for move in picking_moves:
                    move_id = move.id or move._origin.id
                    product_id = move.product_id.id
                    warehouse_id = move._warehouse_id()

                    svl_move = move.stock_valuation_layer_ids
                    svl_quantity = sum(svl_move.mapped('quantity'))

                    if (product_id, warehouse_id) in new_costs:
                        former_cost = new_costs[(product_id, warehouse_id)]
                    else:
                        former_cost = 0.0
                        if svl_quantity:
                            svl_value = sum(svl_move.mapped('value'))
                            former_cost = svl_value / svl_quantity

                    additional_cost = 0.0
                    if split_method == 'equal':
                        additional_cost = currency.round(cost_per_move / svl_quantity)

                    elif split_method == 'by_quantity':
                        additional_cost = currency.round(svl_quantity * cost_per_qty)
                    
                    elif split_method == 'by_current_cost_price':
                        additional_cost = currency.round((factors[move_id] * extra_cost) / svl_quantity)

                    new_cost = former_cost + additional_cost
                    values += [{
                        'cost_line_id': cost_line_id,
                        'move_id': move_id,
                        'product_id': product_id,
                        'service_product_id': cost_line.product_id.id,
                        'warehouse_id': warehouse_id,
                        'qty': svl_quantity,
                        'uom_id': move.product_id.uom_id.id,
                        'former_cost': former_cost,
                        'additional_cost': additional_cost,
                        'new_cost': new_cost,
                        'split_method_lite': split_method,
                        'partner_id': cost_line.partner_id.id
                    }]
                    new_costs[product_id, warehouse_id] = new_cost
            
        return values

    def compute_landed_cost(self):
        for cost in self:
            valuation_values = [(5,)]
            for line_values in cost._get_product_cost_lines():
                move = self.env['stock.move'].browse(line_values['move_id'])
                valuation_values += [(0, 0, {
                    'cost_line_id': line_values['cost_line_id'],
                    'move_id': line_values['move_id'],
                    'warehouse_id': line_values['warehouse_id'],
                    'product_id': line_values['product_id'],
                    'quantity': line_values['qty'],
                    'former_cost': line_values['former_cost'],
                    'additional_landed_cost': line_values['additional_cost']
                })]
            cost.valuation_adjustment_lines = valuation_values

    @api.onchange('vendor_bill', 'vendor_bill_id')
    def _onchange_vendor_bill(self):
        if self.vendor_bill != 'draft_bill':
            return
        
        vendor_bill = self.vendor_bill_id

        cost_lines_values = [(5,)]
        for invoice_line in vendor_bill.invoice_line_ids:
            cost_lines_values += [(0, 0, {
                'bill_id': vendor_bill.id,
                'product_id': invoice_line.product_id.id,
                'partner_id': vendor_bill.partner_id.id,
                'name': invoice_line.name,
                'account_id': invoice_line.account_id.id,
                'split_method_lite': 'equal',
                'split_method': 'equal',
                'price_unit': invoice_line.price_unit
            })]

        self.cost_lines = cost_lines_values


    def button_validate(self):
        for rec in self:
            if rec.vendor_bill == 'create_bill':
                rec.button_validate_for_create_bill()
            elif rec.vendor_bill == 'draft_bill':
                rec.update_draft_bill()
        return True

    def button_validate_for_create_bill(self):
        self._check_can_validate()
        cost_without_adjusment_lines = self.filtered(lambda c: not c.valuation_adjustment_lines)
        if cost_without_adjusment_lines:
            cost_without_adjusment_lines.compute_landed_cost()
        if not self._check_sum():
            raise UserError(_('Cost and adjustments lines do not match. You should maybe recompute the landed costs.'))

        for cost in self:
            cost = cost.with_company(cost.company_id)
            valuation_layers = cost.product_cost_lines._update_valuations()
            in_layers = valuation_layers.filtered(lambda o: o.value > 0.0)

            line_partners = cost.cost_lines.mapped('partner_id')
            partner_id = line_partners and line_partners[0].id or False
            vendor_bill_journal = self.env['account.journal'].search([
                ('company_id', '=', cost.company_id.id), 
                ('type', '=', 'purchase')
            ], limit=1)

            move_vals_list = []
            for partner in cost.cost_lines.mapped('partner_id'):
                partner_lines = cost.cost_lines.filtered(lambda o: o.partner_id == partner)
                partner_layers = in_layers.filtered(lambda o: o.landed_partner_id == partner)
                move_vals_list += [{
                    'partner_id': partner.id,
                    'invoice_date': fields.Datetime.now(),
                    'journal_id': vendor_bill_journal.id,
                    'move_type': 'in_invoice',
                    'invoice_line_ids': [(0, 0, {
                        'name': o.product_id.display_name,
                        'product_id': o.product_id.id,
                        'account_id': o.account_id.id,
                        'quantity': 1,
                        'price_unit': o.price_unit,
                    }) for o in partner_lines]
                }]

            moves = self.env['account.move'].create(move_vals_list)
            moves._post()

            cost.write({
                'state': 'done', 
                'account_move_ids': [(6, 0, moves.ids)]
            })

            # if cost.vendor_bill_id and cost.vendor_bill_id.state == 'posted' and cost.company_id.anglo_saxon_accounting:
            #     all_amls = cost.vendor_bill_id.line_ids | cost.account_move_id.line_ids
            #     for product in cost.cost_lines.product_id:
            #         accounts = product.product_tmpl_id.get_product_accounts()
            #         input_account = accounts['stock_input']
            #         all_amls.filtered(lambda aml: aml.account_id == input_account and not aml.full_reconcile_id).reconcile()

        return True

    def update_draft_bill(self):
        self._check_can_validate()
        cost_without_adjusment_lines = self.filtered(lambda c: not c.valuation_adjustment_lines)
        if cost_without_adjusment_lines:
            cost_without_adjusment_lines.compute_landed_cost()
        if not self._check_sum():
            raise UserError(_('Cost and adjustments lines do not match. You should maybe recompute the landed costs.'))

        for cost in self:
            cost = cost.with_company(cost.company_id)
            valuation_layers = cost.product_cost_lines._update_valuations()
            in_layers = valuation_layers.filtered(lambda o: o.value > 0.0)

            cost.vendor_bill_id.write({
                'invoice_line_ids': [(0, 0, {
                    'name': o.product_id.display_name,
                    'product_id': o.product_id.id,
                    'account_id': o.account_id.id,
                    'quantity': 1,
                    'price_unit': o.price_unit,
                }) for o in cost.cost_lines]
            })

            cost.vendor_bill_id.invoice_date = fields.Date.today()
            cost.vendor_bill_id._post()
            cost.write({
                'state': 'done',
                'account_move_ids': [(6, 0, cost.vendor_bill_id.ids)]
            })

            # if cost.vendor_bill_id and cost.vendor_bill_id.state == 'posted' and cost.company_id.anglo_saxon_accounting:
            #     all_amls = cost.vendor_bill_id.line_ids | cost.account_move_id.line_ids
            #     for product in cost.cost_lines.product_id:
            #         accounts = product.product_tmpl_id.get_product_accounts()
            #         input_account = accounts['stock_input']
            #         all_amls.filtered(lambda aml: aml.account_id == input_account and not aml.full_reconcile_id).reconcile()
        return True

    def action_view_vendor_bills(self):
        self.ensure_one()
        domain = [('id', 'in', self.account_move_ids.ids)]
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_in_invoice_type")
        return dict(action, domain=domain)

    def action_view_journal_entries(self):
        self.ensure_one()
        domain = [('id', 'in', self.stock_valuation_layer_ids.mapped('account_move_id').ids)]
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_journal_line")
        return dict(action, domain=domain)

    def _debug_product_cost(self):
        try:
            from prettytable import PrettyTable
        except ImportError:
            return

        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        table = PrettyTable()

        products = self.product_cost_lines.mapped('product_id')
        lines = self.env['stock.valuation.layer.line'].sudo().search([('product_id', 'in', products.ids)])

        if is_cost_per_warehouse:
            rows = []
            for product in products:
                for warehouse in lines.filtered(lambda o: o.product_id == product).mapped('warehouse_id'):
                    rows += [[
                        product.display_name,
                        warehouse.display_name,
                        product.with_context(price_for_warehouse=warehouse.id).standard_price
                    ]]

            table.field_names = ["Product", "Warehouse", "Cost"]
        else:
            rows = []
            for product in products:
                rows += [[
                    product.display_name,
                    product.standard_price
                ]]

            table.field_names = ["Product", "Cost"]
        table.add_rows(rows)

        print(table)

    def _debug_svl(self):
        try:
            from prettytable import PrettyTable
        except ImportError:
            return

        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        table = PrettyTable()

        products = self.product_cost_lines.mapped('product_id')
        lines = self.env['stock.valuation.layer.line'].sudo().search([('product_id', 'in', products.ids)])

        rows = []
        for line in lines:
            rows += [[
                line.svl_id.id,
                line.product_id.display_name,
                line.location_id.display_name,
                line.quantity,
                line.unit_cost,
                line.value,
                line.remaining_qty,
                line.remaining_value,
                line.sale_line_purchase_price
            ]]

        table.field_names = ["SVL", "Product", "Location", "Quantity", "Unit Cost", "Value", "Rem. Qty", "Rem. Value", "Purchase Price"]
        table.add_rows(rows)

        print(table)
    

class StockLandedCostLine(models.Model):
    _inherit = 'stock.landed.cost.lines'
    
    split_method_lite = fields.Selection(
        [('equal', 'Equal'),('by_quantity', 'By Quantity'),('by_current_cost_price', 'By Current Cost'),],
        string='Split Method',
        required=True,
        default='equal',
        help="Equal : Cost will be equally divided.\n"
             "By Quantity : Cost will be divided according to product's quantity.\n"
             "By Current cost : Cost will be divided according to product's current cost.\n")

    bill_id = fields.Many2one('account.move', string='Vendor Bill')
    partner_id = fields.Many2one('res.partner', string='Vendor')
    
    @api.onchange('split_method_lite', 'split_method')
    def _onchange_split_method(self):
        if self.split_method_lite:
            self.split_method = self.split_method_lite

    @api.onchange('product_id')
    def onchange_product_id(self):
        super(StockLandedCostLine, self).onchange_product_id()
        self.account_id = self.product_id.categ_id.property_account_expense_categ_id.id


class AdjustmentLines(models.Model):
    _inherit = 'stock.valuation.adjustment.lines'

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True)
            

class ProductCostLines(models.Model):
    _name = 'product.cost.lines'
    _description = 'Product Cost Lines'
    
    cost_id = fields.Many2one('stock.landed.cost', 'Landed Cost', required=True, ondelete='cascade')
    cost_line_id = fields.Many2one('stock.landed.cost.lines', 'Landed Cost Lines', required=False)
    move_id = fields.Many2one('stock.move', string='Stock Move', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True)
    picking_id = fields.Many2one('stock.picking', string='Transfer Document', related='move_id.picking_id')
    name = fields.Char(string='Name', related='picking_id.name')
    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    service_product_id = fields.Many2one(comodel_name='product.product', string='Service Product')
    qty = fields.Integer(string='Quantity')
    uom_id = fields.Many2one(comodel_name='uom.uom', string='UoM')
    former_cost = fields.Float(string='Former Cost')
    additional_cost = fields.Float(string='Additional Cost')
    new_cost = fields.Float(string='New Cost')

    split_method_lite = fields.Selection(
        [('equal', 'Equal'),('by_quantity', 'By Quantity'),('by_current_cost_price', 'By Current Cost'),],
        string='Split Method',
        required=True,
        default='equal',
        help="Equal : Cost will be equally divided.\n"
             "By Quantity : Cost will be divided according to product's quantity.\n"
             "By Current cost : Cost will be divided according to product's current cost.\n")

    partner_id = fields.Many2one('res.partner', string='Vendor')

    def _update_valuations(self):
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        svl_vals_list = []
        for line in self:
            landed_cost = line.cost_id
            company_id = landed_cost.company_id
            currency_id = company_id.currency_id

            linked_layer = line.move_id.stock_valuation_layer_ids[:1]

            move = line.move_id
            move_svls = move.stock_valuation_layer_ids
            warehouse_id = move._warehouse_id()
            location_id = move._location_id()

            quantity = sum(move_svls.mapped('quantity'))
            additional_unit_cost = line.additional_cost
            additional_cost = additional_unit_cost * quantity
            if line.split_method_lite == 'by_quantity':
                additional_cost = additional_unit_cost
                additional_unit_cost /= quantity

            svl_line_values = []
            for svl_line in move_svls.line_ids:
                svl_line_values += [{
                    'quantity': 0,
                    'unit_cost': 0,
                    'value': additional_unit_cost * quantity,
                    'lot_id': svl_line.lot_id.id,
                    'description': _('Landed Cost (%s)' % (landed_cost.name,))
                }]
                value_to_add = svl_line.remaining_qty * additional_unit_cost
                if not currency_id.is_zero(value_to_add):
                    svl_line.remaining_value += value_to_add
                    svl_line.svl_id.remaining_value += value_to_add
                
                for child_svl_line in self.env['stock.valuation.layer.line'].search([('svl_source_line_id', '=', svl_line.id)]):
                    svl_line_values += [{
                        'quantity': 0,
                        'unit_cost': 0,
                        'value': additional_unit_cost * child_svl_line.quantity,
                        'lot_id': svl_line.lot_id.id,
                        'description': _('Landed Cost (%s)' % (landed_cost.name,))
                    }]

                    sale_line = child_svl_line.stock_move_id.sale_line_id
                    if not sale_line:
                        continue

                    new_cost = ((sale_line.product_uom_qty * sale_line.purchase_price) + ((abs(child_svl_line.quantity) / svl_line.quantity) * additional_cost)) / sale_line.product_uom_qty
                    sale_line.landed_cost = new_cost - sale_line.purchase_price

            svl_additional_cost = sum(o['value'] for o in svl_line_values)
            svl_lot_ids = [o['lot_id'] for o in svl_line_values if o['lot_id']]

            svl_vals_list += [{
                'company_id': company_id.id,
                'product_id': line.product_id.id,
                'description': _('Landed Cost (%s)' % (landed_cost.name,)),
                'value': svl_additional_cost,
                'quantity': 0,
                'unit_cost': 0,
                'warehouse_id': warehouse_id,
                'location_id': location_id,
                'stock_valuation_layer_id': linked_layer.id,
                'stock_landed_cost_id': landed_cost.id,
                'lot_ids': [(6, 0, svl_lot_ids)],
                'line_ids': [(0, 0, v) for v in svl_line_values],
                'landed_partner_id': line.partner_id.id,
                'landed_service_product_id': line.service_product_id.id
            }]

        stock_valuation_layers = self.env['stock.valuation.layer'].create(svl_vals_list)

        groups = defaultdict(lambda: self.env['stock.valuation.layer'])
        for svl in stock_valuation_layers:
            groups[svl.product_id, svl.warehouse_id, svl.company_id] |= svl.stock_valuation_layer_id

        for (product, warehouse, company), linked_layers in groups.items():

            product_contexed = product.with_company(company)
            if is_cost_per_warehouse:
                product_contexed = product_contexed.with_context(price_for_warehouse=warehouse.id)

            if product.cost_method == 'fifo':
                domain = [
                    ('company_id', '=', company.id),
                    ('product_id', '=', product.id),
                    ('remaining_qty', '>', 0.0)
                ]
                if is_cost_per_warehouse:
                    domain += [('warehouse_id', '=', warehouse.id)]
                
                next_candidate = self.env['stock.valuation.layer.line'].sudo().search(domain, limit=1)
                if next_candidate:
                    product_contexed.with_context(disable_auto_svl=True).standard_price = next_candidate.remaining_value / next_candidate.remaining_qty

            elif product.cost_method == 'average':
                quantity_svl = product_contexed.quantity_svl
                if not float_is_zero(quantity_svl, precision_rounding=product.uom_id.rounding):
                    value_svl = product_contexed.value_svl
                    product_contexed.with_context(disable_auto_svl=True).standard_price = value_svl / quantity_svl

        account_move_vals_list = []
        for svl in stock_valuation_layers:
            # prepare journal entries
            account_move_vals_list  += [svl._prepare_account_move_vals()]

        if account_move_vals_list:
            self.env['account.move']._query_create(account_move_vals_list)

        return stock_valuation_layers
