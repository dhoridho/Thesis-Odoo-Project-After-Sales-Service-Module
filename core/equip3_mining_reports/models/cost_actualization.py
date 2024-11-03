from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.osv import expression

COST_ACT_ACCOUNT_TYPES = [
	'account.data_account_type_payable',
	'account.data_account_type_credit_card',
	'account.data_account_type_current_liabilities',
	'account.data_account_type_non_current_liabilities',
	'account.data_account_type_expenses'
]


class MiningCostActualization(models.Model):
    _name = 'mining.cost.actualization'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Mining Cost Actualization'
    
    @api.model
    def create(self, values):
        if values.get('name', _('New')) == _('New'):
            values['name'] = self.env['ir.sequence'].next_by_code('mining.cost.actualization', sequence_date=None) or _('New')
        return super(MiningCostActualization, self).create(values)

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id', False)
        if default_branch_id:
            return default_branch_id
        return self.env.branch.id if len(self.env.branches) == 1 else False

    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids)]

    @api.depends('line_ids', 'line_ids.cost')
    def _compute_total_cost(self):
        for record in self:
            record.total_cost = sum(record.line_ids.mapped('cost'))

    name = fields.Char(default=_('New'), required=True, readonly=True, copy=False)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    is_branch_required = fields.Boolean(related='company_id.show_branch')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    branch_id = fields.Many2one('res.branch', string='Branch', default=_default_branch, domain=_domain_branch, readonly=True, states={'draft': [('readonly', False)]}, tracking=True)
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'), 
            ('post', 'Posted'), 
            ('cancel', 'Cancelled')
        ],
        required=True,
        copy=False,
        default='draft',
        tracking=True
    )
    create_uid = fields.Many2one('res.users', default=lambda self: self.env.user, readonly=True)
    date_from = fields.Date(string='From Date', readonly=True, states={'draft': [('readonly', False)]}, default=fields.Date.today(), tracking=True)
    date_to = fields.Date(string='To Date', readonly=True, states={'draft': [('readonly', False)]}, default=fields.Date.today(), tracking=True)
    mpa_ids = fields.Many2many('mining.production.record', readonly=True, states={'draft': [('readonly', False)]}, string='Actualizations', copy=False, domain="[('state', '=', 'confirmed'), ('prod_rec_date', '>=', date_from), ('prod_rec_date', '<=', date_to)]")
    account_move_id = fields.Many2one('account.move', string='Journal Entry', copy=False, readonly=True)
    line_ids = fields.One2many('mining.cost.actualization.line', 'mining_cost_actualization_id', string='Cost Lines')
    valuation_line_ids = fields.One2many('mining.cost.actualization.valuation', 'mining_cost_actualization_id', string='Valuation Adjusments', readonly=True)
    production_line_ids = fields.One2many('mining.cost.actualization.production','mining_cost_actualization_id', string='Production Cost Lines', readonly=True)
    total_cost = fields.Monetary(string='Total', compute=_compute_total_cost)

    @api.constrains('line_ids')
    def _constrains_line_ids(self):
        for record in self:
            if not record.line_ids:
                raise ValidationError(_('Please set Cost Lines!'))

    @api.onchange('date_from', 'date_to')
    def _onchange_date_from_to(self):
        domain = [('state', '=', 'confirmed')]
        if self.date_from:
            domain.append(('prod_rec_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('prod_rec_date', '<=', self.date_to))

        if self.date_from and self.date_to:
            mpa_ids = self.env['mining.production.record'].search(domain)
            self.mpa_ids = [(6, 0, mpa_ids.ids)]

    def action_validate(self):
        self.ensure_one()
        self.action_compute()
        self.account_move_id = self.env['account.move'].create(self._prepare_move_vals())
        self.account_move_id.action_post()
        self.production_line_ids._create_valuations()
        self.state = 'post' 

    def action_cancel(self):
        self.ensure_one()
        self.state = 'cancel'

    def _prepare_move_vals(self):
        self.ensure_one()
        product_ids = self.valuation_line_ids.mapped('product_id')

        if not product_ids:
            raise ValidationError(_("There's no valuations!"))

        journal_id = False
        products = []
        for product_id in product_ids:
            if product_id.categ_id.property_stock_journal:
                journal_id = product_id.categ_id.property_stock_journal
                break
            products.append('- %s' % product_id.display_name)
        products = '\n'.join(products)

        if not journal_id:
            raise ValidationError(_('You have to set Stock Journal for any of these products first!\n%s' % products))

        line_ids = []
        for line in self.valuation_line_ids:
            if line.product_id.categ_id.property_valuation != 'real_time':
                raise ValidationError(_('Set category of product %s to Automated first!' % line.product_id.display_name))

            account_id = line.product_id.categ_id.property_stock_valuation_account_id
            name = '%s - %s' % (line.production_id.name, line.product_id.display_name)

            line_ids += [
                (0, 0, {
                    'account_id': line.account_id.id,
                    'name': name,
                    'debit': 0.0,
                    'credit': line.add_cost,
                }),
                (0, 0, {
                    'account_id': account_id.id,
                    'name': name,
                    'debit': line.add_cost,
                    'credit': 0.0,
                })
            ]

        values = {
            'ref': self.name,
            'date': fields.Datetime.now(),
            'discount_type': 'global',
            'journal_id': journal_id.id,
            'line_ids': line_ids
        }

        return values

    def action_compute(self):
        self.ensure_one()

        not_processing_mpas = self.mpa_ids.filtered(lambda o: o.selected_operation_type != 'processing')
        processing_mpas = self.mpa_ids - not_processing_mpas
        n_lines = len(not_processing_mpas) + len(processing_mpas.mapped('production_record_output_ids'))

        total_qty = sum(not_processing_mpas.mapped('nett_total')) + sum(processing_mpas.mapped('output_total'))

        valuation_values = []
        for mpa in self.mpa_ids:
            for line in self.line_ids:
                if mpa.selected_operation_type != 'processing':
                    if line.split_method == 'equal':
                        add_cost = line.cost / n_lines
                    else:
                        add_cost = (mpa.nett_total / total_qty) * line.cost
                    valuation_values += [{
                        'mining_cost_actualization_id': self.id,
                        'company_id': self.company_id.id,
                        'production_id': mpa.id,
                        'product_id': mpa.product_id.id,
                        'quantity': mpa.nett_total,
                        'category': line.cost_category,
                        'account_type': line.account_type,
                        'account_id': line.account_id.id,
                        'add_cost': add_cost
                    }]
                else:
                    for out in mpa.production_record_output_ids:
                        if line.split_method == 'equal':
                            add_cost = line.cost / n_lines
                        else:
                            add_cost = (out.quantity / total_qty) * line.cost

                        valuation_values += [{
                            'mining_cost_actualization_id': self.id,
                            'company_id': self.company_id.id,
                            'production_id': mpa.id,
                            'product_id': out.product_id.id,
                            'quantity': out.quantity,
                            'category': line.cost_category,
                            'account_type': line.account_type,
                            'account_id': line.account_id.id,
                            'add_cost': add_cost,
                            'output_id': out.id
                        }]

        valuation_line_ids = self.env['mining.cost.actualization.valuation'].create(valuation_values)
        self.valuation_line_ids = [(6, 0, valuation_line_ids.ids)]

        production_values = []
        for mpa in self.mpa_ids:
            valuations = self.valuation_line_ids.filtered(lambda v: v.production_id == mpa)
            svls = mpa.stock_valuation_layer_ids
            if mpa.selected_operation_type != 'processing':
                former_cost = abs(sum(svls.mapped('value')))
                production_values += [{
                    'mining_cost_actualization_id': self.id,
                    'company_id': self.company_id.id,
                    'production_id': mpa.id,
                    'product_id': mpa.product_id.id,
                    'quantity': mpa.nett_total,
                    'former_cost': former_cost,
                    'total_material': sum(valuations.filtered(lambda v: v.category == 'material').mapped('add_cost')),
                    'total_overhead': sum(valuations.filtered(lambda v: v.category == 'overhead').mapped('add_cost')),
                    'total_labor': sum(valuations.filtered(lambda v: v.category == 'labor').mapped('add_cost')),
                    'total_subcontracting': sum(valuations.filtered(lambda v: v.category == 'subcontracting').mapped('add_cost'))
                }]
            else:
                for out in mpa.production_record_output_ids:
                    out_valuations = valuations.filtered(lambda o: o.output_id == out)
                    out_svls = svls.filtered(lambda o: o.mining_output_id == out)
                    former_cost = abs(sum(out_svls.mapped('value')))
                    production_values += [{
                        'mining_cost_actualization_id': self.id,
                        'company_id': self.company_id.id,
                        'production_id': mpa.id,
                        'output_id': out.id,
                        'product_id': out.product_id.id,
                        'quantity': out.quantity,
                        'former_cost': former_cost,
                        'total_material': sum(out_valuations.filtered(lambda v: v.category == 'material').mapped('add_cost')),
                        'total_overhead': sum(out_valuations.filtered(lambda v: v.category == 'overhead').mapped('add_cost')),
                        'total_labor': sum(out_valuations.filtered(lambda v: v.category == 'labor').mapped('add_cost')),
                        'total_subcontracting': sum(out_valuations.filtered(lambda v: v.category == 'subcontracting').mapped('add_cost'))
                    }]

        production_line_ids = self.env['mining.cost.actualization.production'].create(production_values)
        self.production_line_ids = [(6, 0, production_line_ids.ids)]


class MiningCostActualizationLine(models.Model):
    _name = 'mining.cost.actualization.line'
    _description = 'Mining Cost Actualization Line'

    @api.model
    def _default_allowed_account_types(self):
        return [(6, 0, [self.env.ref(xml_id).id for xml_id in COST_ACT_ACCOUNT_TYPES])]

    def _compute_allowed_account_types(self):
        self.allowed_account_type_ids = self._default_allowed_account_types()

    @api.model
    def _get_account_type_selection(self):
        selection = []
        for xml_id in COST_ACT_ACCOUNT_TYPES:
            account_type_id = self.env.ref(xml_id)
            selection += [(str(account_type_id.id), account_type_id.display_name)]
        return selection

    mining_cost_actualization_id = fields.Many2one('mining.cost.actualization', copy=False, required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    product_id = fields.Many2one('product.product', string='Product')
    cost_category = fields.Selection(
        selection=[
            ('material', 'Material'), 
            ('overhead', 'Overhead'), 
            ('labor', 'Labor'), 
            ('subcontracting', 'Subcontracting')
        ],
        required=True,
        string='Cost Category'
    )

    account_type = fields.Selection(selection=_get_account_type_selection, string='Account Type')
    allowed_account_type_ids = fields.Many2many('account.account.type', compute=_compute_allowed_account_types, default=_default_allowed_account_types)
    
    account_id = fields.Many2one('account.account', string='Account', required=True, domain="[('user_type_id', 'in', allowed_account_type_ids)]")
    description = fields.Char(string='Description', copy=False)
    split_method = fields.Selection(
        selection=[
            ('equal', 'Equal'), 
            ('by_quantity', 'By Quantity')
        ],
        string='Split Method',
        required=True,
        default='equal'
    )
    cost = fields.Monetary(string='Cost')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.cost_category = self.product_id.manuf_cost_category
            self.cost = self.product_id.standard_price

            product_manuf_account_id = self.product_id.manuf_account_id
            if product_manuf_account_id:
                self.account_id = product_manuf_account_id.id
                self.account_type = str(product_manuf_account_id.user_type_id.id)
            
    @api.onchange('cost_category')
    def _onchange_cost_category(self):
        if self.cost_category:
            self.description = dict(self.fields_get(allfields=['cost_category'])['cost_category']['selection']).get(self.cost_category, False)


class MiningCostActualizationValuation(models.Model):
    _name = 'mining.cost.actualization.valuation'
    _description = 'Mining Cost Actualization Valuation Adjusment'

    @api.model
    def _default_allowed_account_types(self):
        return [(6, 0, [self.env.ref(xml_id).id for xml_id in COST_ACT_ACCOUNT_TYPES])]

    def _compute_allowed_account_types(self):
        self.allowed_account_type_ids = self._default_allowed_account_types()

    @api.model
    def _get_account_type_selection(self):
        selection = []
        for xml_id in COST_ACT_ACCOUNT_TYPES:
            account_type_id = self.env.ref(xml_id)
            selection += [(str(account_type_id.id), account_type_id.display_name)]
        return selection

    mining_cost_actualization_id = fields.Many2one('mining.cost.actualization', copy=False, required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    production_id = fields.Many2one('mining.production.record', string='Actualization', required=True, readonly=True, copy=False)
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure')
    category = fields.Selection(
        string='Category',
        selection=[
            ('material', 'Material'), 
            ('overhead', 'Overhead'), 
            ('labor', 'Labor'), 
            ('subcontracting', 'Subcontracting')
        ],
        required=True,
        readonly=True,
        copy=False
    )

    output_id = fields.Many2one('mining.production.record.line.output', string='Processing Output')

    account_type = fields.Selection(selection=_get_account_type_selection, string='Account Type')
    allowed_account_type_ids = fields.Many2many('account.account.type', compute=_compute_allowed_account_types, default=_default_allowed_account_types)
    
    account_id = fields.Many2one('account.account', string='Account', required=True, domain="[('user_type_id', 'in', allowed_account_type_ids)]")
    add_cost = fields.Monetary(string='Additional Cost', required=True, readonly=True, copy=False)


class MiningCostActualizationProduction(models.Model):
    _name = 'mining.cost.actualization.production'
    _description = 'Mining Cost Actualization Production Cost Lines'

    @api.depends('total_material', 'total_overhead', 'total_labor', 'total_subcontracting', 'former_cost')
    def _compute_total(self):
        for record in self:
            total = record.total_material + record.total_overhead + record.total_labor + record.total_subcontracting
            new_cost = total + record.former_cost
            
            record.total = total
            record.new_cost = new_cost

    def _create_valuations(self):
        for line in self:
            line.svl_id = self.env['stock.valuation.layer'].create({
                'value': line.total,
                'unit_cost': 0,
                'quantity': 0,
                'remaining_qty': 0,
                'description': line.mining_cost_actualization_id.name,
                'product_id': line.product_id.id,
                'company_id': line.company_id.id,
                'mining_type': 'overhead',
                'mining_production_order_id': line.production_id.daily_production_id.id,
                'mining_production_record_id': line.production_id.id
            })
    
    mining_cost_actualization_id = fields.Many2one('mining.cost.actualization', copy=False, required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    production_id = fields.Many2one('mining.production.record', string='Actualization', required=True, readonly=True, copy=False)
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure')

    output_id = fields.Many2one('mining.production.record.line.output', string='Processing Output')

    total_material = fields.Monetary(string='Total Material', required=True, readonly=True, copy=False)
    total_labor = fields.Monetary(string='Total Labor', required=True, readonly=True, copy=False)
    total_overhead = fields.Monetary(string='Total Overhead', required=True, readonly=True, copy=False)
    total_subcontracting = fields.Monetary(string='Total Subcontracting', required=True, readonly=True, copy=False)
    
    former_cost = fields.Monetary(string='Former Cost', required=True, readonly=True, copy=False)
    total = fields.Monetary(string='Total Cost', compute=_compute_total)
    new_cost = fields.Monetary(string='New Cost', compute=_compute_total)

    svl_id = fields.Many2one('stock.valuation.layer', string='Valuation')
