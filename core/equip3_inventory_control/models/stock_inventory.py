# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz
import json
from datetime import datetime, date, timedelta
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import float_compare, float_is_zero, float_round
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons.equip3_inventory_operation.models.qiscus_connector import qiscus_request
from odoo.addons.equip3_approval_hierarchy.models.approval_hierarchy import ApprovalHierarchy


class StockInventory(models.Model):
    _inherit = 'stock.inventory'
    _description = "Inventory Adjustment"
    _rec_name = 'inv_ref'
    
    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Stock Count'),
            'template': '/equip3_inventory_control/static/xls/stock_count_template.xlsx'
        }]

    @api.model
    def create(self, vals):
        sequence_code = 'inv.adj.value.seq' if vals.get('is_adj_value') is True else 'inv.adj.seq'
        vals['inv_ref'] = self.env['ir.sequence'].next_by_code(sequence_code)

        vals.update(self._inventoried_product_sanity_check(vals.get('inventoried_product')))
        return super(StockInventory, self).create(vals)

    def write(self, vals):
        vals.update(self._inventoried_product_sanity_check(vals.get('inventoried_product')))
        return super(StockInventory, self).write(vals)

    @api.model
    def _inventoried_product_sanity_check(self, inventoried_product):
        vals = {}
        if inventoried_product in ('all_product', 'specific_category'):
            vals['product_ids'] = [(5,)]
            if inventoried_product == 'all_product':
                vals['product_categories'] = [(5,)]
        elif inventoried_product == 'specific_product':
            vals['product_categories'] = [(5,)]
        return vals

    @api.model
    def _selection_type_stock_custom(self):
        selection = [
            ('all_product', 'All Products'),
            ('specific_product', 'Specific Products'),
            ('specific_category', 'Specific Categories')
        ]
        return selection

    warehouse_id = fields.Many2one(
        'stock.warehouse', string="Warehouse", tracking=True, required=True)
    user_id = fields.Many2one('res.users', string="Responsible", tracking=True)
    inventoried_product = fields.Selection(
        _selection_type_stock_custom, string="Inventoried Product", default='all_product', tracking=True)
    is_adj_value = fields.Boolean(string="Input Unit Price")
    is_counted_qty = fields.Boolean(
        string="Is Counted Quantities", compute='_compute_counted_qty', store=False, readonly=True)
    adjustment_account_id = fields.Many2one(
        'account.account', string="Adjustment Account")
    filtered_adjustment_account_id = fields.Many2many(
        'account.account', string="Filter Adjustment Account", compute="_compute_filtered_adjustment_account_id")
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Groups',
                                        default=lambda self: self.env.user.analytic_tag_ids.filtered(lambda a: a.company_id == self.env.company).ids)
    is_analytic_mandatory = fields.Boolean(
        compute='compute_is_analytic_mandatory')
    is_analytic_readonly_dup = fields.Boolean(
        compute="compute_is_analytic_readonly", default=True)
    state = fields.Selection(string='Status', selection_add=[
        ('confirm', ),
        ('completed', 'Completed'),
        ('to_approve', 'Waiting for Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')],
        copy=False, index=True, readonly=True, tracking=True,
        default='draft')
    inv_state = fields.Selection(related='state', tracking=False, string='Status 0')
    inv_state_1 = fields.Selection(related='state', tracking=False, string='Status 1')
    branch_id = fields.Many2one(
        'res.branch', string='Branch',
        default=lambda self: self.env.branches if len(self.env.branches) == 1 else False,
        domain=lambda self: [('id', 'in', self.env.branches.ids)], tracking=True)

    approval_matrix_id = fields.Many2one(
        'stock.inventory.approval.matrix', string="Approval Matrix", compute='_get_approval_matrix')
    is_stock_count_approval = fields.Boolean(
        string="Stock Count Approval", store=True)
    approved_matrix_ids = fields.One2many('stock.inventory.approval.matrix.line', 'st_inv_id',
                                          compute="_compute_approving_matrix_lines_inv", store=True, string="Approved Matrix")
    approval_matrix_line_id = fields.Many2one(
        'stock.inventory.approval.matrix.line', string='Material Approval Matrix Line', compute='_compute_approval_matrix_line_id', store=False)
    is_approve_button = fields.Boolean(
        string='Is Approve Button', compute='_compute_is_approve_button', store=False)
    inv_ref = fields.Char(default="New", readonly=True)

    product_categories = fields.Many2many(
        'product.category', 'category_id', 'p_id', string="Product Category", tracking=True)
    description = fields.Text(string="Description", tracking=True)

    is_mbs_on_stock_count_and_inventory_adjustment = fields.Boolean(
        string="Stock Count and Inventory Adjustment", compute='_compute_stock_count_and_inventory_adjustment')
    uom_conversion_ids = fields.One2many(
        'uom.conversion.history', 'si_uom_id', string="Uom Conversion")
    inv_cost = fields.Boolean(string='Is Invoice Cost',
                              compute='_compute_get_value_from_config')
    domain_warehouse_id = fields.Char(
        'Warehouse Domain', compute="_compute_location")
    freeze_inventory = fields.Boolean(default=False, string='Freeze Inventory')
    freeze_inventory_from_config = fields.Boolean(default=False, store=True)

    def _get_freeze_button_from_config(self, res):
        freeze_inventory_from_config = self.env['ir.config_parameter'].sudo(
        ).get_param('mandatory_freeze_inventory', False)
        res.update({
            'freeze_inventory_from_config': freeze_inventory_from_config,
            'freeze_inventory' : freeze_inventory_from_config
        })

    @api.depends('branch_id')
    def _compute_location(self):
        if self.env.branches.ids:
            warehouse_ids = self.env['stock.warehouse'].search(
                [('branch_id', 'in', self.env.branches.ids)])
            if warehouse_ids:
                self.domain_warehouse_id = json.dumps(
                    [('id', 'in', warehouse_ids.ids)])
            else:
                self.domain_warehouse_id = json.dumps([])
        else:
            self.domain_warehouse_id = json.dumps([])

    def _compute_get_value_from_config(self):
        self.inv_cost = eval(self.env['ir.config_parameter'].sudo().get_param('inv_cost', 'False'))

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        context = dict(self.env.context) or {}
        is_stock_count_approval = self.env['ir.config_parameter'].sudo(
        ).get_param('is_stock_count_approval')
        domain = domain or []
        if 'is_inv_adj_acc' in context:
            if is_stock_count_approval:
                # domain.extend([('state', 'in', ('approved', 'done'))])

                stock_inventory = self._get_stock_inventory_records()
                domain.extend([('id', 'in', stock_inventory.ids)])
                # domain.extend(['&', '|', ('approval_matrix_id', '!=', False), ('state', 'in', ('approved', 'done')), '&', ('approval_matrix_id', '=', False), ('state', 'in', ('completed', 'done'))])

            else:
                domain.extend([('state', 'in', ('completed', 'done'))])
        return super(StockInventory, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)


    def _get_stock_inventory_records(self):
        stock_inventory = self.env['stock.inventory'].search([
            ('state', 'in', ('completed', 'approved', 'done'))
        ])
        approval_record = stock_inventory.filtered(
            lambda r: r.approval_matrix_id and r.state in ('approved', 'done'))
        not_approval_record = stock_inventory.filtered(
            lambda r: not r.approval_matrix_id and r.state in
            ('completed', 'done'))
        stock_inventory_record = approval_record + not_approval_record
        return stock_inventory_record

    @api.depends('is_stock_count_approval','approval_matrix_id')
    def _get_approve_button(self):
        for record in self:
            matrix_line = sorted(record.approved_matrix_ids.filtered(
                lambda r: not r.approved), key=lambda r: r.sequence)
            if len(matrix_line) == 0:
                record.is_approve_button = False
                record.approval_matrix_line_id = False
            elif len(matrix_line) > 0:
                matrix_line_id = matrix_line[0]
                if self.env.user.id in matrix_line_id.user_ids.ids and self.env.user.id != matrix_line_id.last_approved.id:
                    record.is_approve_button = True
                    record.approval_matrix_line_id = matrix_line_id.id
                else:
                    record.is_approve_button = False
                    record.approval_matrix_line_id = False
            else:
                record.is_approve_button = False
                record.approval_matrix_line_id = False

    @api.depends('approved_matrix_ids', 'approved_matrix_ids.approved', 'approved_matrix_ids.sequence')
    def _compute_approval_matrix_line_id(self):
        for record in self:
            matrix_lines = sorted(self.approved_matrix_ids.filtered(lambda r: not r.approved), key=lambda r: r.sequence)
            approval_matrix_line_id = False
            if len(matrix_lines) > 0:
                matrix_line = matrix_lines[0]
                if self.env.user.id in matrix_line.user_ids.ids and self.env.user.id != matrix_line.last_approved.id:
                    approval_matrix_line_id = matrix_line.id
            record.approval_matrix_line_id = approval_matrix_line_id

    @api.depends('approval_matrix_line_id')
    def _compute_is_approve_button(self):
        for record in self:
            is_approve_button = False
            if record.approval_matrix_line_id:
                is_approve_button = True
            record.is_approve_button = is_approve_button

    def _compute_stock_count_and_inventory_adjustment(self):
        is_mbs_on_stock_count_and_inventory_adjustment = self.env['ir.config_parameter'].sudo(
        ).get_param('is_mbs_on_stock_count_and_inventory_adjustment', False)
        for record in self:
            record.is_mbs_on_stock_count_and_inventory_adjustment = is_mbs_on_stock_count_and_inventory_adjustment

    @api.depends('approval_matrix_id')
    def _compute_approving_matrix_lines_inv(self):
        data = [(5, 0, 0)]
        for record in self:
            counter = 0
            record.approved_matrix_ids = []
            hierarchy = ApprovalHierarchy()
            for line in record.approval_matrix_id.si_approval_matrix_line_ids:
                if line.approver_types == "specific_approver":
                    counter += 1
                    data.append((0, 0, {
                        'sequence' : counter,
                        'user_ids' : [(6, 0, line.user_ids.ids)],
                        'minimum_approver' : line.minimum_approver,
                    }))
                elif line.approver_types == "by_hierarchy":
                    manager_ids = []
                    seq = 1
                    data_seq = 0
                    approvers = hierarchy.get_hierarchy(self, self.env.user.employee_id, data_seq, manager_ids, seq,
                                                        line.minimum_approver)
                    for user in approvers:
                        counter += 1
                        data.append((0, 0, {
                            'sequence': counter,
                            'user_ids': [(6, 0, [user])],
                            'minimum_approver': 1,
                        }))
            record.approved_matrix_ids = data

    @api.depends('warehouse_id')
    def _get_approval_matrix(self):
        for record in self:
            matrix_id = self.env['stock.inventory.approval.matrix'].search(
                [('warehouse_id', '=', record.warehouse_id.id)], limit=1)
            record.approval_matrix_id = matrix_id

    @api.onchange('warehouse_id')
    def _onchage_warhouse_branch(self):
        self._compute_stock_count_and_inventory_adjustment()

    def inv_request_for_approving(self):
        for record in self:
            values = {
                'sender': self.env.user,
                'name': 'Stock Count',
                'no': record.inv_ref,
                'datetime': fields.Datetime.now(),
                'action_xmlid': 'stock.action_inventory_form',
                'menu_xmlid': 'stock.menu_action_inventory_form'
            }

            for approver in record.approved_matrix_ids.mapped('user_ids'):
                values.update({'receiver': approver})
                qiscus_request(record, values)
            record.write({'state': 'to_approve'})

    def inv_approving(self):
        is_inventory_adjustment_with_value = self.env['ir.config_parameter'].sudo(
        ).get_param('is_inventory_adjustment_with_value', False)
        for record in self:
            user = self.env.user
            if record.is_approve_button and record.approval_matrix_line_id:
                approval_matrix_line_id = record.approval_matrix_line_id
                if user.id in approval_matrix_line_id.user_ids.ids and \
                        user.id not in approval_matrix_line_id.approved_users.ids:
                    name = approval_matrix_line_id.state_char or ''
                    utc_datetime = datetime.now()
                    local_timezone = pytz.timezone(self.env.user.tz)
                    local_datetime = utc_datetime.replace(tzinfo=pytz.utc)
                    local_datetime = local_datetime.astimezone(
                        local_timezone).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    if name != '':
                        name += "\n • %s: Approved - %s" % (
                            self.env.user.name, local_datetime)
                    else:
                        name += "• %s: Approved - %s" % (
                            self.env.user.name, local_datetime)

                    approval_matrix_line_id.write({
                        'last_approved': self.env.user.id, 'state_char': name,
                        'approved_users': [(4, user.id)]})
                    if approval_matrix_line_id.minimum_approver == len(approval_matrix_line_id.approved_users.ids):
                        approval_matrix_line_id.write(
                            {'time_stamp': datetime.now(), 'approved': True})
                        # next_approval_matrix_line_id = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
                        # if next_approval_matrix_line_id and len(next_approval_matrix_line_id[0].approver) > 1:
                        #     pass
            if len(record.approved_matrix_ids) == len(record.approved_matrix_ids.filtered(lambda r: r.approved)):
                record.write({'state': 'approved'})
            if is_inventory_adjustment_with_value:
                record.write({'accounting_date': fields.Date.today()})

    def inv_reject(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Stock Inventory Matrix',
            'res_model': 'stock.inventory.request.matrix.reject',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    def set_to_draft_inv(self):
        for record in self:
            record.write({'state': 'draft'})

    @api.depends('is_analytic_readonly_dup')
    def compute_is_analytic_mandatory(self):
        user = self.env.user
        for record in self:
            if user.has_group('analytic.group_analytic_tags'):
                record.is_analytic_mandatory = True
            else:
                record.is_analytic_mandatory = False

    def compute_is_analytic_readonly(self):
        for record in self:
            group_allow_validate_inventory_adjustment = self.env['ir.config_parameter'].sudo(
            ).get_param('is_inventory_adjustment_with_value', False)
            if not group_allow_validate_inventory_adjustment:
                record.is_analytic_readonly_dup = False
            else:
                record.is_analytic_readonly_dup = True

    def _compute_filtered_adjustment_account_id(self):
        self.filtered_adjustment_account_id = [(6, 0, [])]

    def _compute_counted_qty(self):
        self.is_counted_qty = not self.env.user.has_group('equip3_inventory_accessright_setting.group_allow_see_onhand_difference')

    @api.model
    def default_get(self, fields):
        res = super(StockInventory, self).default_get(fields)
        self.get_approval_matrix_from_config(res)
        group_allow_see_onhand_difference = self.env.user.has_group(
            'equip3_inventory_accessright_setting.group_allow_see_onhand_difference')
        if not group_allow_see_onhand_difference:
            res['prefill_counted_quantity'] = 'zero'
        self._get_freeze_button_from_config(res)
        return res

    def get_approval_matrix_from_config(self, res):
        is_stock_count_approval_config = self.env['ir.config_parameter'].sudo(
        ).get_param('is_stock_count_approval')
        if is_stock_count_approval_config:
            res.update({'is_stock_count_approval': True})
        else:
            res.update({'is_stock_count_approval': False})

    @api.onchange('adjustment_account_id')
    def _onchange_adjustment_account_id(self):
        self.line_ids.update({'adjustment_account_id': self.adjustment_account_id.id})

    @api.constrains('location_ids', 'state')
    def _check_location_ids(self):
        for rec in self.filtered(lambda o: o.state != 'draft'):
            location_ids = rec.location_ids
            records = self.search([
                ('location_ids', 'in', location_ids.ids),
                ('is_adj_value', '=', rec.is_adj_value),
                ('state', '=', 'confirm'),
                ('id', '!=', rec.id)
            ])
            if records:
                message = '\n'.join(['- %s on %s' % (
                    ', '.join([location.display_name for location in location_ids & record.location_ids]),
                    record.inv_ref)
                for record in records])
                raise ValidationError(_('An Inventory Adjustment has been conducted on the following location(s):\n%s' % (message)))

    @api.onchange('warehouse_id')
    def set_domain_for_location_ids(self):
        return {'domain': {
            'location_ids': "[('company_id', '=', company_id), ('usage', 'in', ['transit', 'internal']), ('id', 'child_of', %s)]" % self.warehouse_id.view_location_id.id
        }}

    @api.onchange('inventoried_product')
    def _onchange_inventoried_prduct(self):
        self.update(self._inventoried_product_sanity_check(self.inventoried_product))

    def _create_uom_histories(self):
        self.ensure_one()
        values = {}
        """
        Not implemented yet.

        line_values = []
        uom_history_values = []
        for line in self.line_ids:
            if line.uom_id != line.product_id.uom_id:
                quantity = line.uom_id._compute_quantity(line.product_qty, line.product_id.uom_id)
                uom_history_values += [(0, 0, {
                    'product_id': line.product_id.id,
                    'location_id': line.location_id.id,
                    'partner_id': line.partner_id.id,
                    'product_qty': line.product_qty,
                    'uom_id': line.uom_id.id,
                    'counted_qty': quantity,
                    'uom_conversion': line.product_id.uom_id.id,
                    'prod_lot_id': line.prod_lot_id.id
                })]

                line_values += [(1, line.id, {'product_qty': quantity})]

        if uom_history_values:
            values.update({'uom_conversion_ids': uom_history_values})

        if line_values:
            values.update({'line_ids': line_values})"""
        return values

    def action_complete(self):
        self.ensure_one()
        
        if not self.env.context.get('skip_check_tracked_lines', False):
            res = self._check_tracked_lines()
            if res is not True:
                return res
        
        is_stock_count_approval_config = self.env['ir.config_parameter'].sudo().get_param('is_stock_count_approval')
        if (self.is_stock_count_approval or is_stock_count_approval_config) and not self.approval_matrix_id:
            raise ValidationError(_('Please set approval matrix for Stock Count first!\nContact Administrator for more details.'))

        if len(self.line_ids) < 1:
            raise ValidationError(
                ('You have to fill this line if you want to click the button complete inventory'))

        values = {'state': 'completed'}
        values.update(self._create_uom_histories())
        self.write(values)
        return True

    def action_open_inventory_lines_after_continue(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'name': _('Inventory Lines'),
            'res_model': 'stock.inventory.line',
        }
        context = dict(self.env.context) or {}
        context.update({
            'default_is_editable': True,
            'default_inventory_id': self.id,
            'default_company_id': self.company_id.id,
            'is_inv_adj_acc': context.get('is_inv_adj_acc') if context.get('is_inv_adj_acc') else True
        })
        # Define domains and context
        domain = [
            ('inventory_id', '=', self.id),
            ('location_id.usage', 'in', ['internal', 'transit'])
        ]
        if self.location_ids:
            context['default_location_id'] = self.location_ids[0].id
            if len(self.location_ids) == 1:
                if not self.location_ids[0].child_ids:
                    context['readonly_location_id'] = True

        if self.product_ids or self.prefill_counted_quantity == "zero" or self.state in ('completed',):
            action['view_id'] = self.env.ref('stock.stock_inventory_line_tree_no_product_create').id
            if len(self.product_ids) == 1:
                context['default_product_id'] = self.product_ids[0].id
        else:
            action['view_id'] = self.env.ref('stock.stock_inventory_line_tree').id

        action['context'] = context
        action['domain'] = domain
        return action

    def action_open_inventory_lines(self):
        self.ensure_one()
        res = super(StockInventory, self).action_open_inventory_lines()
        action = {
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'name': _('Inventory Lines'),
            'res_model': 'stock.inventory.line',
        }
        context = res.get('context', {})
        context.update({
            'default_is_editable': True,
            'default_inventory_id': self.id,
            'default_company_id': self.company_id.id,
            'is_inv_adj_acc': context.get('is_inv_adj_acc') if context.get('is_inv_adj_acc') else True
        })
        # Define domains and context
        domain = [
            ('inventory_id', '=', self.id),
            ('location_id.usage', 'in', ['internal', 'transit'])
        ]
        if self.location_ids:
            context['default_location_id'] = self.location_ids[0].id
            if len(self.location_ids) == 1:
                if not self.location_ids[0].child_ids:
                    context['readonly_location_id'] = True

        if self.product_ids:
            action['view_id'] = self.env.ref('stock.stock_inventory_line_tree_no_product_create').id
            if len(self.product_ids) == 1:
                context['default_product_id'] = self.product_ids[0].id
        else:
            action['view_id'] = self.env.ref(
                'stock.stock_inventory_line_tree_no_product_create').id

        if self.prefill_counted_quantity == "zero":
            action['view_id'] = self.env.ref('stock.stock_inventory_line_tree_no_product_create').id

        if self.state in ('completed', 'approved', 'done'):
            action['view_id'] = self.env.ref('equip3_inventory_control.stock_inventory_line_tree_no_product_create_account_adj').id

        action['context'] = context
        action['domain'] = domain
        return action

    def _get_inventory_lines_values(self):
        values = super(StockInventory, self)._get_inventory_lines_values()
        for sequence, vals in enumerate(values):
            vals.update({
                'sequence': sequence + 1,
                'uom_id': vals.get('product_uom_id', False)
            })
        return values

    def smart_button_for_inv_accounting(self):
        context = dict(self.env.context) or {}
        context.update({
            'create': False,
            'is_inv_adj_acc': False,
            'is_from_stock_count': True
        })
        return {
            "name": "Stock Inventory",
            "view_mode": "form",
            "res_model": "stock.inventory",
            "view_id": [(self.env.ref('stock.view_inventory_form').id)],
            "type": "ir.actions.act_window",
            "target": "current",
            "res_id": self.id,
            "context": context
        }

    def _get_quantities(self):
        self.ensure_one()
        where_clause = [
            'sq.company_id = %s' % self.company_id.id,
            'sq.quantity != 0',
        ]

        if self.location_ids:
            domain_loc = [('id', 'child_of', self.location_ids.ids)]
        else:
            domain_loc = [('company_id', '=', self.company_id.id), ('usage', 'in', ['internal', 'transit'])]
        locations_ids = [l['id'] for l in self.env['stock.location'].search_read(domain_loc, ['id'])]

        where_clause += ['sq.location_id IN %s']
        args = (tuple(locations_ids),)

        if self.prefill_counted_quantity == 'zero':
            where_clause += ['pp.active IS True']

        if self.product_categories:
            where_clause += ['pp.categ_id IN %s']
            args += (tuple(self.product_categories.ids),)

        elif self.product_ids:
            where_clause += ['pp.id IN %s']
            args += (tuple(self.product_ids.ids),)

        where_clause = ' AND '.join(where_clause)

        query = """
        SELECT
            sq.product_id,
            sq.location_id,
            sq.lot_id,
            sq.package_id,
            sq.owner_id,
            SUM(sq.quantity) AS quantity
        FROM
            stock_quant sq
        LEFT JOIN
            product_product pp
            ON (pp.id = sq.product_id)
        LEFT JOIN
            product_template pt
            ON (pt.id = pp.product_tmpl_id)
        WHERE
            {}
        GROUP BY
            sq.product_id,
            sq.location_id,
            sq.lot_id,
            sq.package_id,
            sq.owner_id
        """.format(where_clause)

        self.env.cr.execute(query, args)
        return {(
            quant['product_id'] and quant['product_id'] or False,
            quant['location_id'] and quant['location_id'] or False,
            quant['lot_id'] and quant['lot_id'] or False,
            quant['package_id'] and quant['package_id'] or False,
            quant['owner_id'] and quant['owner_id'] or False):
            quant['quantity'] for quant in self.env.cr.dictfetchall()
        }

    def action_wizard_save(self):
        return True

    def clear_cache_old_data_custom(self):
        all_data = self.search(
            [('inventoried_product', 'in', ('all_product', False)), ('state', '!=', 'draft')])
        for data in all_data:
            data.product_ids = False

    @api.onchange('force_date')
    def onchange_force_date(self):
        for rec in self:
            if rec.force_date:
                rec.write({'accounting_date': rec.force_date})

    # def _register_hook(self):
    #     super(StockInventory, self)._register_hook()
    #     InventoryIn._patch_method('_get_inventory_lines_values', _get_inventory_lines_values)


class InventoryLine(models.Model):
    _inherit = "stock.inventory.line"

    sequence = fields.Char(string="No")
    adjustment_account_id = fields.Many2one(
        'account.account', related='inventory_id.adjustment_account_id', string="Adjustment Account")
    is_adj_val = fields.Boolean(
        related="inventory_id.is_adj_value", string="Value")
    analytic_tag_ids = fields.Many2many(
        'account.analytic.tag', string='Analytic Groups', related="inventory_id.analytic_tag_ids", readonly='1')
    product_cost_method = fields.Selection(related='product_id.cost_method')

    """ This field was created for the case when the user wants to use a different uom,
    but to implement this, it's necessary to add a quantity field in the uom as well
    (product_uom_qty & difference_uom_qty for example).
    So, currently this field is not functional. """
    uom_id = fields.Many2one('uom.uom', string='UoM')

    # TODO: delete these fields
    category_uom_id = fields.Many2one('uom.category', string='uom category')
    filtered_adjustment_account_id = fields.Many2many('account.account', string="Filter Adjustment Account", compute="_compute_adjustment_account_id")

    def _compute_adjustment_account_id(self):
        self.filtered_adjustment_account_id = [(6, 0, [])]


class StockInventoryLogs(models.Model):
    _inherit = 'stock.inventory.log'
    _description = 'Stock Count Logs'

    inventory_id = fields.Many2one(string='Stock Count')

    def _prepare_cron_values(self):
        res = super(StockInventoryLogs, self)._prepare_cron_values()
        res['name'] = res.get('name', '').replace('Inventory Adjustment', 'Stock Count')
        return res
