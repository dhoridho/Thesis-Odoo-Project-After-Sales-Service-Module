from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class AgriCostActualization(models.Model):
    _name = 'agri.cost.actualization'
    _description = 'Agriculture Cost Actualization'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def create(self, values):
        if values.get('name', _('New')) == _('New'):
            values['name'] = self.env['ir.sequence'].next_by_code('agri.cost.actualization', sequence_date=None) or _('New')
        return super(AgriCostActualization, self).create(values)

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id', False)
        if default_branch_id:
            return default_branch_id
        return self.env.branch.id if len(self.env.branches) == 1 else False

    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id', '=', self.env.company.id)]

    name = fields.Char(default=_('New'), required=True, readonly=True, copy=False)
    date_from = fields.Date(string='Start Date', readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: fields.Date.today() - relativedelta(days=1), tracking=True)
    date_to = fields.Date(string='End Date', readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: fields.Date.today(), tracking=True)
    crop_activity_ids = fields.Many2many('crop.activity', readonly=True, states={'draft': [('readonly', False)]}, required=True, string='Activity', tracking=True)
    activity_line_ids = fields.Many2many('agriculture.daily.activity.line', readonly=True, states={'draft': [('readonly', False)]}, domain="[('activity_id', 'in', crop_activity_ids)]", string='Activity Lines')
    account_move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True, tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True, readonly=True, tracking=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    branch_id = fields.Many2one('res.branch', readonly=True, states={'draft': [('readonly', False)]}, default=_default_branch, domain=_domain_branch, required=True, tracking=True)

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

    line_ids = fields.One2many('agri.cost.actualization.line', 'actualization_id', string='Cost Lines')
    valuation_line_ids = fields.One2many('agri.cost.actualization.valuation', 'actualization_id', string='Valuation Adjusments', readonly=True)
    production_line_ids = fields.One2many('agri.cost.actualization.production','actualization_id', string='Agriculture Cost Lines', readonly=True)
    total_cost = fields.Monetary(string='Total', compute='_compute_total_cost')

    @api.depends('line_ids', 'line_ids.cost')
    def _compute_total_cost(self):
        for record in self:
            record.total_cost = sum(record.line_ids.mapped('cost'))

    @api.constrains('date_from', 'date_to')
    def _check_date(self):
        for record in self:
            if record.date_to < record.date_from:
                raise ValidationError(_('End date cannot be smaller than start date!'))

    @api.constrains('line_ids')
    def _check_line_ids(self):
        for record in self:
            if not record.line_ids:
                raise ValidationError(_('Please set Cost Lines!'))

    @api.onchange('date_from', 'date_to', 'crop_activity_ids')
    def _onchange_date_from_to(self):
        domain = [('activity_id', 'in', self.crop_activity_ids.ids)]
        if self.date_from:
            domain.append(('date_scheduled', '>=', self.date_from))
        if self.date_to:
            domain.append(('date_scheduled', '<=', self.date_to))

        if self.date_from and self.date_to:
            activity_line_ids = self.env['agriculture.daily.activity.line'].search(domain)
            self.activity_line_ids = [(6, 0, activity_line_ids.ids)]

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

    def _prepare_move_line_vals(self, product_id, quantity):
        account_id = product_id.categ_id.property_stock_valuation_account_id
        return {
            'name': product_id.display_name,
            'ref': product_id.display_name,
            'product_id': product_id.id,
            'product_uom_id': product_id.uom_id.id,
            'quantity': quantity,
            'account_id': account_id.id,
            'debit': 0.0,
            'credit': 0.0
        }

    def _prepare_move_vals(self):
        self.ensure_one()
        product_ids = self.valuation_line_ids.mapped('product_id')

        if not product_ids:
            raise ValidationError(_("There's no valuations!"))

        default_type, default_journal = self.env['ir.property']._get_default_property('property_stock_journal', 'product.category')
        if default_type != 'many2one':
            raise ValidationError(_('Please set default Stock Valuation Journal first!'))
        journal_id = default_journal[1]

        line_ids = []
        for line in self.valuation_line_ids:
            name = '%s - %s' % (line.activity_line_id.name, line.product_id.display_name)

            if line.activity_line_id.activity_type == 'harvest':
                product_qty = line.harvest_id.product_qty
            elif line.activity_line_id.activity_type == 'planting':
                product_qty = line.nursery_id.product_qty
            else:
                product_qty = line.crop_id.product_qty
            
            move_line_values = {
                'name': name,
                'product_id': line.product_id.id,
                'product_uom_id': line.product_id.uom_id.id,
                'quantity': product_qty,
                'account_id': line.account_id.id,
                'debit': 0.0,
                'credit': line.add_cost
            }

            line_ids += [(0, 0, move_line_values)]

        default_type, default_account = self.env['ir.property']._get_default_property('property_stock_valuation_account_id', 'product.category')
        if default_type != 'many2one':
            raise ValidationError(_('Please set default Stock Valuation Account first!'))
        stock_valuation_account_id = default_account[1]

        total_debit = sum([line[-1]['credit'] for line in line_ids])
        debit_move_line_values = {
            'name': ' - '.join([line.activity_line_id.name for line in self.valuation_line_ids]),
            'account_id': stock_valuation_account_id,
            'debit': total_debit,
            'credit': 0.0
        }

        line_ids = [(0, 0, debit_move_line_values)] + line_ids

        values = {
            'ref': self.name,
            'journal_id': journal_id,
            'date': fields.Date.today(),
            'move_type': 'entry',
            'line_ids': line_ids,
            'company_id': self.company_id.id,
            'branch_id': self.branch_id.id
        }

        return values

    def action_compute(self):
        self.ensure_one()

        activity_line_ids = self.activity_line_ids

        harvest_activities = activity_line_ids.filtered(lambda o: o.activity_type == 'harvest')
        planting_activities = activity_line_ids.filtered(lambda o: o.activity_type == 'planting')
        other_activities = activity_line_ids.filtered(lambda o: o.activity_type not in ('harvest', 'planting'))
        
        n_lines = 0
        if harvest_activities:
            n_lines += sum([len(harvest.harvest_ids) for harvest in harvest_activities])
        if planting_activities:
            n_lines += sum([len(planting.nursery_ids) for planting in planting_activities])
        if other_activities:
            n_lines += sum([len(other.crop_ids) for other in other_activities])
        
        total_qty = 0.0
        for activity_line in activity_line_ids:
            activity_line_type = activity_line.activity_type
            if activity_line_type == 'harvest':
                total_qty += sum(activity_line.harvest_ids.mapped('product_qty'))
            elif activity_line_type == 'planting':
                total_qty += sum(activity_line.nursery_ids.mapped('product_qty'))
            else:
                total_qty += sum(activity_line.crop_ids.mapped('product_qty'))

        valuation_values = []
        for activity_line in activity_line_ids:
            activity_line_type = activity_line.activity_type
            for line in self.line_ids:
                if activity_line_type == 'harvest':
                    for harvest in activity_line.harvest_ids:
                        if line.split_method == 'equal':
                            add_cost = line.cost / n_lines
                        else:
                            add_cost = (harvest.product_qty / total_qty) * line.cost

                        valuation_values += [{
                            'actualization_id': self.id,
                            'activity_line_id': activity_line.id,
                            'product_id': harvest.product_id.id,
                            'quantity': harvest.product_qty,
                            'category': line.cost_category,
                            'account_id': line.account_id.id,
                            'add_cost': add_cost,
                            'harvest_id': harvest.id
                        }]
                elif activity_line_type == 'planting':
                    for nursery in activity_line.nursery_ids:
                        if line.split_method == 'equal':
                            add_cost = line.cost / n_lines
                        else:
                            add_cost = (nursery.product_qty / total_qty) * line.cost

                        valuation_values += [{
                            'actualization_id': self.id,
                            'activity_line_id': activity_line.id,
                            'product_id': nursery.product_id.id,
                            'quantity': nursery.product_qty,
                            'category': line.cost_category,
                            'account_id': line.account_id.id,
                            'add_cost': add_cost,
                            'nursery_id': nursery.id
                        }]

                else:
                    for crop in activity_line.crop_ids:
                        if line.split_method == 'equal':
                            add_cost = line.cost / n_lines
                        else:
                            add_cost = (crop.product_qty / total_qty) * line.cost

                        valuation_values += [{
                            'actualization_id': self.id,
                            'activity_line_id': activity_line.id,
                            'product_id': crop.crop.id,
                            'quantity': crop.product_qty,
                            'category': line.cost_category,
                            'account_id': line.account_id.id,
                            'add_cost': add_cost,
                            'crop_id': crop.id
                        }]

        valuation_line_ids = self.env['agri.cost.actualization.valuation'].create(valuation_values)
        self.valuation_line_ids = [(6, 0, valuation_line_ids.ids)]

        production_values = []
        for activity_line in activity_line_ids:
            valuations = self.valuation_line_ids.filtered(lambda v: v.activity_line_id == activity_line)
            svls = activity_line.stock_valuation_layer_ids
            activity_line_type = activity_line.activity_type
            if activity_line_type == 'harvest':
                for harvest in activity_line.harvest_ids:
                    harvest_valuations = valuations.filtered(lambda o: o.harvest_id == harvest)
                    harvest_svls = svls.filtered(lambda o: o.stock_move_id == harvest)
                    former_cost = abs(sum(harvest_svls.mapped('value')))
                    production_values += [{
                        'actualization_id': self.id,
                        'activity_line_id': activity_line.id,
                        'harvest_id': harvest.id,
                        'product_id': harvest.product_id.id,
                        'quantity': harvest.product_qty,
                        'former_cost': former_cost,
                        'total_material': sum(harvest_valuations.filtered(lambda v: v.category == 'material').mapped('add_cost')),
                        'total_overhead': sum(harvest_valuations.filtered(lambda v: v.category == 'overhead').mapped('add_cost')),
                        'total_labor': sum(harvest_valuations.filtered(lambda v: v.category == 'labor').mapped('add_cost')),
                        'total_subcontracting': sum(harvest_valuations.filtered(lambda v: v.category == 'subcontracting').mapped('add_cost'))
                    }]
            elif activity_line_type == 'planting':
                for nursery in activity_line.nursery_ids:
                    nursery_valuations = valuations.filtered(lambda o: o.nursery_id == nursery)
                    nursery_svls = svls.filtered(lambda o: o.stock_move_id.nursery_id == nursery)
                    former_cost = abs(sum(nursery_svls.mapped('value')))
                    production_values += [{
                        'actualization_id': self.id,
                        'activity_line_id': activity_line.id,
                        'nursery_id': nursery.id,
                        'product_id': nursery.product_id.id,
                        'quantity': nursery.product_qty,
                        'former_cost': former_cost,
                        'total_material': sum(nursery_valuations.filtered(lambda v: v.category == 'material').mapped('add_cost')),
                        'total_overhead': sum(nursery_valuations.filtered(lambda v: v.category == 'overhead').mapped('add_cost')),
                        'total_labor': sum(nursery_valuations.filtered(lambda v: v.category == 'labor').mapped('add_cost')),
                        'total_subcontracting': sum(nursery_valuations.filtered(lambda v: v.category == 'subcontracting').mapped('add_cost'))
                    }]
            else:
                material_value = abs(sum(activity_line.material_ids.stock_valuation_layer_ids.mapped('value')))
                crops_total_quantity = sum(activity_line.crop_ids.mapped('product_qty'))

                for crop in activity_line.crop_ids:
                    crop_valuations = valuations.filtered(lambda o: o.crop_id == crop)
                    former_cost = (crop.product_qty / crops_total_quantity) * material_value
                    production_values += [{
                        'actualization_id': self.id,
                        'activity_line_id': activity_line.id,
                        'crop_id': crop.id,
                        'product_id': crop.crop.id,
                        'quantity': crop.product_qty,
                        'former_cost': former_cost,
                        'total_material': sum(crop_valuations.filtered(lambda v: v.category == 'material').mapped('add_cost')),
                        'total_overhead': sum(crop_valuations.filtered(lambda v: v.category == 'overhead').mapped('add_cost')),
                        'total_labor': sum(crop_valuations.filtered(lambda v: v.category == 'labor').mapped('add_cost')),
                        'total_subcontracting': sum(crop_valuations.filtered(lambda v: v.category == 'subcontracting').mapped('add_cost'))
                    }]

        production_line_ids = self.env['agri.cost.actualization.production'].create(production_values)
        self.production_line_ids = [(6, 0, production_line_ids.ids)]


class AgriCostActualizationLine(models.Model):
    _name = 'agri.cost.actualization.line'
    _description = 'Agriculture Cost Actualization Line'

    actualization_id = fields.Many2one('agri.cost.actualization', copy=False, required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', related='actualization_id.company_id')
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

    account_id = fields.Many2one('account.account', string='Account', required=True)
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
        self.description = self.product_id.display_name


class AgriCostActualizationValuation(models.Model):
    _name = 'agri.cost.actualization.valuation'
    _description = 'Agriculture Cost Actualization Valuation Adjusment'


    actualization_id = fields.Many2one('agri.cost.actualization', copy=False, required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', related='actualization_id.company_id')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    activity_line_id = fields.Many2one('agriculture.daily.activity.line', string='Activity Line', required=True, readonly=True, copy=False)
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
    
    account_id = fields.Many2one('account.account', string='Account', required=True)
    add_cost = fields.Monetary(string='Additional Cost', required=True, readonly=True, copy=False)

    harvest_id = fields.Many2one('stock.move', string='Harvest')
    nursery_id = fields.Many2one('agriculture.daily.activity.nursery', string='Nursery')
    crop_id = fields.Many2one('agriculture.crop', string='Crop')


class AgriCostActualizationProduction(models.Model):
    _name = 'agri.cost.actualization.production'
    _description = 'Agriculture Cost Actualization Production Cost Lines'


    @api.depends('total_material', 'total_overhead', 'total_labor', 'total_subcontracting', 'former_cost')
    def _compute_total(self):
        for record in self:
            total = record.total_material + record.total_overhead + record.total_labor + record.total_subcontracting
            new_cost = total + record.former_cost
            
            record.total = total
            record.new_cost = new_cost

    def _create_valuations(self):
        for line in self:
            values = {
                'value': line.total,
                'unit_cost': 0,
                'quantity': 0,
                'remaining_qty': 0,
                'description': line.actualization_id.name,
                'product_id': line.product_id.id,
                'company_id': line.company_id.id
            }
            if line.harvest_id:
                values.update({'stock_move_id': line.harvest_id.id})
            elif line.nursery_id:
                values.update({'stock_move_id': line.nursery_id.stock_move_id.id})
            else:
                values.update({'stock_move_line_id': line.crop_id.move_line_id.id})

            if line.product_id.with_company(line.company_id.id).cost_method in ('average', 'fifo'):
                values.update({'remaining_value': values.get('value', 0.0)})

            line.svl_id = self.env['stock.valuation.layer'].create(values)
    
    actualization_id = fields.Many2one('agri.cost.actualization', copy=False, required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', related='actualization_id.company_id')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    activity_line_id = fields.Many2one('agriculture.daily.activity.line', string='Activity Line', required=True, readonly=True, copy=False)
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure')

    total_material = fields.Monetary(string='Total Material', required=True, readonly=True, copy=False)
    total_labor = fields.Monetary(string='Total Labor', required=True, readonly=True, copy=False)
    total_overhead = fields.Monetary(string='Total Overhead', required=True, readonly=True, copy=False)
    total_subcontracting = fields.Monetary(string='Total Subcontracting', required=True, readonly=True, copy=False)
    
    former_cost = fields.Monetary(string='Former Cost', required=True, readonly=True, copy=False)
    total = fields.Monetary(string='Total Cost', compute=_compute_total)
    new_cost = fields.Monetary(string='New Cost', compute=_compute_total)

    svl_id = fields.Many2one('stock.valuation.layer', string='Valuation')
    harvest_id = fields.Many2one('stock.move', string='Harvest')
    nursery_id = fields.Many2one('agriculture.daily.activity.nursery', string='Nursery')
    crop_id = fields.Many2one('agriculture.crop', string='Crop')
