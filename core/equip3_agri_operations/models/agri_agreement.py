from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AgriAgreementTemplate(models.Model):
    _name = 'agri.agreement.template'
    _description = 'Agri Agreement Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def _default_branch(self):
        company_branches = self.env.branches.filtered(lambda o: o.company_id == self.env.company)
        if len(company_branches) == 1:
            return company_branches.id
        return False

    @api.model
    def _domain_branch(self):
        company_branches = self.env.branches.filtered(lambda o: o.company_id == self.env.company)
        return [('id', 'in', company_branches.ids)]

    name = fields.Char(string='Agri Agreement Template', required=True, copy=False, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    branch_id = fields.Many2one('res.branch', required=True, tracking=True, default=_default_branch, domain=_domain_branch)
    period_start = fields.Date()
    period_end = fields.Date()
    line_ids = fields.One2many('agri.agreement.template.line', 'template_id', string='Lines')

    # technical fields
    agreement_type = fields.Selection(selection=[
        ('plantation', 'Plantation'),
        ('nursery', 'Nursery'),
        ('harvest', 'harvest'),
        ('other', 'Other')
    ], required=True, default='plantation')

    _sql_constraints = [
        ('name_unique', 'unique(agreement_type,name,company_id)', 'Template Name has been set for another Template!')
    ]

    @api.constrains('period_start', 'period_end')
    def _check_period(self):
        for record in self:
            if record.period_end < record.period_start:
                raise ValidationError(_('Period End cannot be earlier than period start!'))


class AgriAgreementTemplateLine(models.Model):
    _name = 'agri.agreement.template.line'
    _description = 'Agri Agreement Template Line'

    @api.model
    def _default_uom(self):
        return self.env.company.crop_default_uom_id.id

    template_id = fields.Many2one('agri.agreement.template', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', related='template_id.company_id')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    price = fields.Monetary()

    activity_id = fields.Many2one('crop.activity', required=True)
    product_id = fields.Many2one('product.product', required=True, domain="[('type', '=', 'service'), ('uom_id.category_id', '=', uom_category_id)]")
    product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', default=1.0)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True, default=_default_uom, domain="[('category_id', '=', uom_category_id)]")
    uom_category_id = fields.Many2one('uom.category', related='uom_id.category_id')

    @api.constrains('product_uom_qty')
    def _check_product_uom_qty(self):
        for record in self:
            if record.product_uom_qty <= 0.0:
                raise ValidationError(_('Quantity must be positive!'))


class AgriAgreement(models.Model):
    _name = 'agri.agreement'
    _description = 'Agri Agreement'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            agreement_type = vals.get('agreement_type', 'plantation')
            vals['name'] = self.env['ir.sequence'].next_by_code('%s.agreement' % agreement_type) or _('New')
        return super(AgriAgreement, self).create(vals)

    @api.model
    def _default_branch(self):
        company_branches = self.env.branches.filtered(lambda o: o.company_id == self.env.company)
        if len(company_branches) == 1:
            return company_branches.id
        return False

    @api.model
    def _domain_branch(self):
        company_branches = self.env.branches.filtered(lambda o: o.company_id == self.env.company)
        return [('id', 'in', company_branches.ids)]

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=_('New'), tracking=True)
    reference = fields.Char(required=True, string='Agreement Name', readonly=True, states={'draft': [('readonly', False)]}, tracking=True)
    partner_id = fields.Many2one('res.partner', required=True, string='Vendor', readonly=True, states={'draft': [('readonly', False)]}, tracking=True)
    date_start = fields.Date(required=True, readonly=True, states={'draft': [('readonly', False)]}, tracking=True)
    date_end = fields.Date(required=True, readonly=True, states={'draft': [('readonly', False)]}, tracking=True)
    estate_id = fields.Many2one('crop.estate', required=True, readonly=True, states={'draft': [('readonly', False)]}, tracking=True)
    branch_id = fields.Many2one('res.branch', required=True, readonly=True, states={'draft': [('readonly', False)]}, tracking=True, default=_default_branch, domain=_domain_branch)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    template_id = fields.Many2one('agri.agreement.template', readonly=True, states={'draft': [('readonly', False)]}, tracking=True, domain="[('agreement_type', '=', agreement_type), ('branch_id', '=', branch_id)]")
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Group', readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('progress', 'In Progress'),
        ('to_close', 'Closed')
    ], required=True, readonly=True, default='draft', copy=False, string='Status', tracking=True)

    contract_ids = fields.One2many('agri.agreement.contract', 'agreement_id', string='Contracts', readonly=True, states={'draft': [('readonly', False)]})
    activity_line_ids = fields.One2many('agriculture.daily.activity.line', 'agreement_id', string='Activity Lines')
    activity_record_ids = fields.One2many('agriculture.daily.activity.record', 'agreement_id', readonly=True, string="Activity Records")
    usage_form_view_ref = fields.Char(compute='_compute_usage_form_view_ref')

    bill_ids = fields.One2many('account.move', 'agri_agreement_id', readonly=True)
    block_ids = fields.Many2many('crop.block', domain="[('use_type', '=', block_use_type)]", string='Blocks')
    block_use_type = fields.Selection(selection=[
        ('block', 'Block'),
        ('nursery_area', 'Nursery Area')
    ], compute='_compute_block_use_type')

    # technical fields
    next_contract_sequence = fields.Integer(compute='_compute_next_contract_sequence')
    bill_data = fields.Text()
    bills_count = fields.Integer(compute='_compute_bills_count')
    can_create_bill = fields.Boolean(compute='_compute_can_create_bill')

    agreement_type = fields.Selection(selection=[
        ('plantation', 'Plantation'),
        ('nursery', 'Nursery'),
        ('harvest', 'harvest'),
        ('other', 'Other')
    ], required=True, default='plantation')

    _sql_constraints = [
        ('reference_unique', 'unique(agreement_type,reference,company_id)', 'Agreement Name has been set for another Agreement!')
    ]

    @api.depends('bill_ids')
    def _compute_bills_count(self):
        for record in self:
            record.bills_count = len(record.bill_ids)

    @api.depends('contract_ids', 'contract_ids.can_create_bill')
    def _compute_can_create_bill(self):
        for record in self:
            record.can_create_bill = any(line.can_create_bill for line in record.contract_ids)

    @api.depends('agreement_type')
    def _compute_block_use_type(self):
        for record in self:
            record.block_use_type = record.agreement_type == 'nursery' and 'nursery_area' or 'block'

    @api.depends('contract_ids')
    def _compute_next_contract_sequence(self):
        for record in self:
            record.next_contract_sequence = len(record.contract_ids) + 1

    @api.depends('agreement_type')
    def _compute_usage_form_view_ref(self):
        for record in self:
            agreement_type = record.agreement_type
            if agreement_type == 'plantation':
                agreement_type = 'daily_activity'
            elif agreement_type == 'other':
                agreement_type += '_activity'
            record.usage_form_view_ref = 'equip3_agri_operations.view_%s_line_form' % agreement_type

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_start and record.date_end and record.date_end < record.date_start:
                raise ValidationError(_('Date end cannot be earlier than date start!'))

    @api.onchange('template_id')
    def _onchange_template_id(self):
        template_id = self.template_id or self.env['agri.agreement.template']
        self.contract_ids = [(5,)] + [(0, 0, {
            'sequence': sequence + 1,
            'activity_id': line.activity_id.id,
            'product_id': line.product_id.id,
            'description': line.product_id.display_name,
            'product_uom_qty': line.product_uom_qty,
            'uom_id': line.uom_id.id,
            'price': line.price
        }) for sequence, line in enumerate(template_id.line_ids)]

    def action_confirm(self):
        self.ensure_one()
        if self.state != 'draft':
            return
        self.state = 'confirm'

    def action_create_activity(self):
        self.ensure_one()
        if self.state not in ('confirm', 'progress'):
            return
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Activity'),
            'res_model': 'agri.agreement.create.activity',
            'target': 'new',
            'view_mode': 'form',
            'context': {
                'default_agreement_id': self.id,
            }
        }

    def _check_state(self):
        today = fields.Date.today()
        to_update = self.sudo().search([('state', '=', 'progress'), ('date_end', '<=', today)])
        to_update.write({'state': 'to_close'})

    def action_create_bill(self, bill_data=None):
        self.ensure_one()
        if not bill_data:
            return {
                'name': _('Create Bill'),
                'type': 'ir.actions.act_window',
                'res_model': 'agri.agreement.create.bill',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_agreement_id': self.id
                }
            }
        
        today = fields.Date.today()
        analytic_tag_ids = self.analytic_tag_ids

        contract_values = []
        invoice_line_values = []
        for line in bill_data:
            to_bill_qty = line['to_bill_qty']
            if to_bill_qty <= 0.0:
                continue
            contract_line = self.env['agri.agreement.contract'].browse(line['contract_id'])
            invoice_line_values += [{
                'product_id': contract_line.product_id.id,
                'name': contract_line.product_id.display_name,
                'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)],
                'quantity': to_bill_qty,
                'product_uom_id': contract_line.uom_id.id,
                'price_unit': contract_line.price,
                'agri_agreement_contract_id': contract_line.id
            }]
        
        ref = self.name
        if len(self.bill_ids) > 0:
            ref += ' - %s' % (len(self.bill_ids) + 1,)
        
        self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': today,
            'analytic_group_ids': [(6, 0, analytic_tag_ids.ids)],
            'date': today,
            'company_id': self.company_id.id,
            'branch_id': self.branch_id.id,
            'agri_agreement_id': self.id,
            'agri_activity_record_ids': [(6, 0, self.activity_line_ids.mapped('activity_record_ids').filtered(lambda o: o.state == 'confirm').ids)],
            'invoice_line_ids': invoice_line_values,
            'ref': ref
        })

        if contract_values:
            self.contract_ids = contract_values

    def action_view_bills(self):
        self.ensure_one()
        if not self.bill_ids:
            return
        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_in_invoice_type')
        if len(self.bill_ids) == 1:
            action.update({
                'views': [(self.env.ref('account.view_move_form').id, 'form')],
                'res_id': self.bill_ids[0].id,
                'target': 'current'
            })
        else:
            action.update({
                'domain': [('id', 'in', self.bill_ids.ids)],
                'target': 'current'
            })
        return action

    def _prepare_account_move_line_values(self, product_id, quantity):
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

    def _prepare_account_moves_values(self, bill):
        self.ensure_one()
        agreement_name = self.name
        company_id = self.company_id
        branch_id = self.branch_id
        contract_lines = self.contract_ids
        currency_id = company_id.currency_id
        today = fields.Date.today()

        default_type, default_journal = self.env['ir.property']._get_default_property('property_stock_journal', 'product.category')
        if default_type != 'many2one':
            raise ValidationError(_('Please set default Stock Valuation Journal first!'))

        journal_id = default_journal[1]
        activity_records = bill.agri_activity_record_ids

        quantities = {}
        move_lines_data = {}
        for record in activity_records:
            move_lines_values = getattr(record, '_%s_account_entry_move' % record.activity_type)(with_move=True)

            total_quantity = 0.0
            move_lines_data[record.id] = {'quantities': [], 'values': []}
            for x, y, move_line_values in move_lines_values['lines']:
                if not move_line_values['debit']:
                    continue
                move_lines_data[record.id]['quantities'] += [move_line_values['quantity']]
                move_lines_data[record.id]['values'] += [move_line_values]
                total_quantity += move_line_values['quantity']
            quantities[record.id] = total_quantity
        
        activity_wise = {}
        for record in activity_records:
            if record.activity_id.id not in activity_wise:
                activity_wise[record.activity_id.id] = record
            else:
                activity_wise[record.activity_id.id] |= record

        def _svl_values(value, product_id):
            values = {
                'value': value,
                'unit_cost': 0,
                'quantity': 0,
                'remaining_qty': 0,
                'description': agreement_name,
                'product_id': product_id,
                'company_id': company_id.id
            }
            if self.env['product.product'].browse(product_id).with_company(company_id.id).cost_method in ('average', 'fifo'):
                values.update({'remaining_value': value})
            return values

        bill_line_ids = bill.invoice_line_ids

        moves_values = []
        for activity_id, records in activity_wise.items():
            line_values = []
            svl_ids = []
            for record in records:
                move_line_data = move_lines_data[record.id]
                for qty, move_line_values in zip(move_line_data['quantities'], move_line_data['values']):
                    amount = currency_id.round((qty / quantities[record.id]) * sum(bill_line_ids.filtered(lambda o: o.agri_agreement_contract_id.activity_id.id == activity_id).mapped('price_total')))
                    move_line_values['debit'] = amount

                    svl_values = _svl_values(amount, move_line_values['product_id'])
                    if 'stock_move_id' in move_line_values:
                        svl_values['stock_move_id'] = move_line_values.pop('stock_move_id')
                    if 'stock_move_line_id' in move_line_values:
                        svl_values['stock_move_line_id'] = move_line_values.pop('stock_move_line_id')

                    svl_ids += [self.env['stock.valuation.layer'].create(svl_values).id]
                    line_values += [move_line_values]

            contract_line = contract_lines.filtered(lambda o: o.activity_id.id == activity_id)
            credit_line_values = self._prepare_account_move_line_values(contract_line.product_id, contract_line.product_uom_qty)
            credit_line_amount = sum([v['debit'] for v in line_values])
            credit_line_values['credit'] = credit_line_amount

            svl_values = _svl_values(credit_line_amount, credit_line_values['product_id'])
            svl_ids += [self.env['stock.valuation.layer'].create(svl_values).id]

            line_values += [credit_line_values]

            moves_values += [{
                'ref': agreement_name,
                'journal_id': journal_id,
                'date': today,
                'move_type': 'entry',
                'line_ids': line_values,
                'company_id': company_id.id,
                'branch_id': branch_id.id,
                'stock_valuation_layer_ids': [(6, 0, svl_ids)]
            }]
        return moves_values

    def _create_valuation(self, bill):
        self.ensure_one()
        move_values = self._prepare_account_moves_values(bill)
        for values in move_values:
            ref = values.pop('ref')
            account_move = self.env['account.move'].create(values)
            account_move._post()
            account_move.ref = ref


class AgriAgreementContract(models.Model):
    _name = 'agri.agreement.contract'
    _description = 'Agri Agreement Contract'

    @api.model
    def _default_uom(self):
        return self.env.company.crop_default_uom_id.id

    agreement_id = fields.Many2one('agri.agreement', required=True, ondelete='cascade')
    sequence = fields.Integer(string='No')
    activity_id = fields.Many2one('crop.activity', required=True)
    product_id = fields.Many2one('product.product', required=True, domain="[('type', '=', 'service'), ('uom_id.category_id', '=', uom_category_id)]")
    description = fields.Text()
    product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', default=1.0)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True, default=_default_uom, domain="[('category_id', '=', uom_category_id)]")
    uom_category_id = fields.Many2one('uom.category', related='uom_id.category_id')
    company_id = fields.Many2one('res.company', related='agreement_id.company_id')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    price = fields.Monetary()

    done_qty = fields.Float(string='Done', digits='Product Unit of Measure', compute='_compute_done_qty')
    to_bill_qty = fields.Float(string='To Bill', digits='Product Unit of Measure', compute='_compute_to_bill')
    billed_qty = fields.Float(string='Billed', digits='Product Unit of Measure', readonly=True, compute='_compute_billed_qty')
    can_create_bill = fields.Boolean(compute='_compute_can_create_bill')

    @api.depends('agreement_id', 'agreement_id.bill_ids', 'agreement_id.bill_ids.state', 'agreement_id.bill_ids.invoice_line_ids',  'agreement_id.bill_ids.invoice_line_ids.quantity', 'agreement_id.bill_ids.invoice_line_ids.agri_agreement_contract_id')
    def _compute_billed_qty(self):
        for record in self:
            invoice_line_ids = record.agreement_id.bill_ids.filtered(lambda o: o.state != 'cancel').mapped('invoice_line_ids').filtered(lambda o: o.agri_agreement_contract_id == record)
            record.billed_qty = sum(invoice_line_ids.mapped('quantity'))

    @api.depends('agreement_id', 'agreement_id.activity_record_ids', 'activity_id', 'uom_id')
    def _compute_done_qty(self):
        for record in self:
            uom_id = record.uom_id
            activity_id = record.activity_id
            done = 0.0
            for activity_record in record.agreement_id.activity_record_ids.filtered(lambda o: o.activity_id == activity_id and o.uom_id.category_id == uom_id.category_id):
                done += activity_record.uom_id._compute_quantity(activity_record.size, uom_id)
            record.done_qty = done

    @api.depends('done_qty', 'billed_qty')
    def _compute_to_bill(self):
        for record in self:
            record.to_bill_qty = record.done_qty - record.billed_qty

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.description = self.product_id and self.product_id.display_name or False

    @api.constrains('product_uom_qty')
    def _check_product_uom_qty(self):
        for record in self:
            if record.product_uom_qty <= 0.0:
                raise ValidationError(_('Quantity must be positive!'))

    @api.depends('to_bill_qty')
    def _compute_can_create_bill(self):
        for record in self:
            record.can_create_bill = record.to_bill_qty > 0
