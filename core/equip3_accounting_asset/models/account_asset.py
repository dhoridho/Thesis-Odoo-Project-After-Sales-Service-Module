
import calendar
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal, ROUND_HALF_UP
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam
import logging
import requests, json
from odoo.tools import date_utils
from lxml import etree
_logger = logging.getLogger(__name__)

headers = {'content-type': 'application/json'}

def float_is_zero(value, precision_rounding):
    if isinstance(value, Decimal):
        epsilon = Decimal(precision_rounding)
    else:
        epsilon = float(precision_rounding)
    return abs(float_round(value, precision_rounding=epsilon)) < epsilon

def float_round(value, precision_rounding):
    if isinstance(value, Decimal):
        rounding_factor = Decimal(precision_rounding)
    else:
        rounding_factor = float(precision_rounding)
    normalized_value = value / rounding_factor  # normalize
    return round(normalized_value) * rounding_factor

class AccountMove(models.Model):
    _inherit = 'account.move'

    is_from_asset = fields.Boolean(string='Is From Asset', default=False)
    account_asset_id = fields.Many2one('account.asset.asset', string='Asset')


    def button_open_invoice_asset(self):
        self.ensure_one()
        action = {
            'name': _("Invoice Asset"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'context': {'create': False},
        }
        # invoice_asset = self.env['account.move'].search([('account_asset_id', '=', self.account_asset_id.id),('move_type', '!=', 'entry')])
        # count_invoice_asset = len(invoice_asset)
        action['domain'] = [('account_asset_id', '=', self.account_asset_id.id),('move_type', '!=', 'entry')]

        return action

    def action_post(self):
        res = super(AccountMove, self).action_post()
        for move in self:
            amount_depreciation = sum(line.debit for line in move.line_ids)
            # move.write({'amount_untaxed': amount_depreciation, 'amount_total': amount_depreciation})
            if not move.account_asset_id:
                asset_id = move.asset_depreciation_ids.mapped('asset_id')
                if asset_id:
                    asset_id = asset_id[0]
                    move_id = self.search([('account_asset_id', '=', asset_id.id), ('move_type', '=', 'entry'), ('state', '=', 'posted')], limit=1)
                    if move_id:
                        raise ValidationError("Depreciation can not be created because the asset is already sold!")
                    for depreciation_line in move.asset_depreciation_ids:
                        depreciation_line.post_lines_and_close_asset()

            elif move.account_asset_id:
                posted_depreciation_lines = move.account_asset_id.depreciation_line_ids.filtered(lambda r: r.move_id and r.move_id.state == 'posted')
                if posted_depreciation_lines:
                    if move.asset_depreciation_ids:
                        raise ValidationError("Asset sales can not be created because depreciation is already sold. Please remove the related journal entry and try again!")

            for line in move.asset_depreciation_ids:
                if line.asset_id.state in ['sold','dispose']:
                    state = line.asset_id.state
                    if state == 'dispose':
                        state = 'disposed'
                    raise ValidationError("You cannot post entries because %s has been %s." % (line.asset_id.name, state))

        return res

    def unlink(self):
        for move in self:
            depreciation_line = self.env['account.asset.depreciation.line'].search([('move_id','=',move.id)])
            for line in depreciation_line:
                line.move_check = False
        return super(AccountMove, self).unlink()

class AccountAssetCategory(models.Model):
    _inherit = 'account.asset.category'


    @api.model
    def _domain_branch(self):
        return [('company_id','=', self.env.company.id)]
    
    journal_id = fields.Many2one('account.journal', string='Journal', domain=_domain_branch, required=True)
        
    cut_off_asset_date = fields.Integer(string='Cut Off Asset Date', default=31)
    date_first_depreciation = fields.Selection([
        ('last_day_period', 'Based on Last Day of Purchase Period'),
        ('manual', 'Manual (Defaulted on Purchase Date)')],
        string='Depreciation Dates', default='manual', required=False,
        help='The way to compute the date of the first depreciation.\n'
             '  * Based on last day of purchase period: The depreciation dates will be based on the last day of the purchase month or the purchase year (depending on the periodicity of the depreciations).\n'
             '  * Based on purchase date: The depreciation dates will be based on the purchase date.')
    account_sales_id = fields.Many2one('account.account', 'Sales Asset Account')
    account_revaluation_surplus_id = fields.Many2one('account.account', 'Revaluation Asset Surplus', required=1)
    account_revaluation_loss_id = fields.Many2one('account.account', 'Revaluation Asset Loss', required=1)
    method = fields.Selection(selection_add=[('double_declining', 'Double Declining')]
                              , ondelete={'double_declining': 'cascade'})
    is_monthly_depreciation = fields.Boolean(string='Monthly Depreciation')
    is_reset_january = fields.Boolean(string='Reset on January')
    account_sales_profit = fields.Many2one('account.account', 'Profit Sale Asset Account', required=1)
    account_sales_loss = fields.Many2one('account.account', 'Loss Sale Asset Account', required=1)
    dispose_account = fields.Many2one('account.account', string='Dispose Account', required=1)
    sequence_id = fields.Many2one('ir.sequence', string='Entry Sequence',
                                  help="This field contains the information related to the numbering of the"
                                       " Asset entries of this Category.",
                                  copy=False)
    set_sequence = fields.Char(string='Set Sequence', required=True)
    sequence_number_next = fields.Integer(string='Next Number',
                                          help='The next sequence number will be used for the next Asset.',
                                          compute='_compute_seq_number_next', inverse='_inverse_seq_number_next')
    is_fiscal_asset_type = fields.Boolean()
    is_convert_to_zero = fields.Boolean(string='Convert Residual to Zero')
    is_include_salvage_value = fields.Boolean(string='Include Salvage Value', default=False)
    prorata_type = fields.Selection([
        ('monthly', 'Monthly Prorata'),
        ('daily', 'Daily Prorata')
    ], string='Prorata Type', default='monthly')


    @api.onchange('is_monthly_depreciation')
    def onchange_monthly_depreciation(self):
        for rec in self:
            if rec.is_monthly_depreciation == False:
                rec.is_reset_january = False


    @api.model
    def _create_sequence(self, vals):
        seq_name = vals['name']
        set_sequence = vals['set_sequence']
        prefix = set_sequence.upper()
        # prefix + '/%(y)s/%(month)s/%(day)s/'
        seq = {
            'name': _('%s Sequence') % seq_name,
            'implementation': 'no_gap',
            'prefix': prefix + '/%(year)s/%(month)s/',
            'padding': 3,
            'number_increment': 1,
            'use_date_range': True,
        }
        if 'company_id' in vals:
            seq['company_id'] = vals['company_id']
        seq = self.env['ir.sequence'].create(seq)
        seq_date_range = seq._get_current_sequence()
        seq_date_range.number_next = vals.get('sequence_number_next', 1)
        return seq

    @api.depends('sequence_id.use_date_range', 'sequence_id.number_next_actual')
    def _compute_seq_number_next(self):
        for asset in self:
            if asset.sequence_id:
                sequence = asset.sequence_id._get_current_sequence()
                asset.sequence_number_next = sequence.number_next_actual
            else:
                asset.sequence_number_next = 1
    def _inverse_seq_number_next(self):
        for asset in self:
            if asset.sequence_id and asset.sequence_number_next:
                sequence = asset.sequence_id._get_current_sequence()
                sequence.sudo().number_next = asset.sequence_number_next
    @api.model
    def create(self, vals):
        if not vals.get('sequence_id'):
            vals.update({'sequence_id': self.sudo()._create_sequence(vals).id})
        asset = super(AccountAssetCategory, self).create(vals)
        return asset

    def write(self, vals):
        for asset in self:
            if ('set_sequence' in vals and asset.set_sequence != vals['set_sequence']):
                if self.env['account.asset.asset'].search([('category_id', 'in', self.ids)], limit=1):
                    raise UserError(_('This Asset Category already contains items, therefore you cannot modify its short name.'))
                set_sequence = vals['set_sequence']
                prefix = set_sequence.upper()
                new_prefix = prefix + '/%(year)s/%(month)s/'
                asset.sequence_id.write({'prefix': new_prefix})
            if ('name' in vals and asset.name != vals['name']):
                seq_name = vals['name']
                asset.sequence_id.write({'name': seq_name})
        return super(AccountAssetCategory, self).write(vals)

    @api.constrains('cut_off_asset_date')
    def _check_cut_off_asset_date(self):
        if self.cut_off_asset_date < 1 or self.cut_off_asset_date > 31:
            raise ValidationError(_('Fill in the Cut off Asset Date with a value between the 1st to 31st.'))
        
        
    @api.onchange('cut_off_asset_date')
    def _onchange_cut_off_asset_date(self):
        if self.cut_off_asset_date < 1 or self.cut_off_asset_date > 31:
            raise ValidationError(_('Fill in the Cut off Asset Date with a value between the 1st to 31st.'))

class Asset(models.Model):
    _inherit = 'account.asset.asset'

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one(
        'res.branch',
        check_company=True,
        domain=_domain_branch,
        default = _default_branch,
        readonly=False, tracking=True)

    is_monthly_depreciation = fields.Boolean(string='Monthly Depreciation')
    is_reset_january = fields.Boolean(string='Reset on January')
    months_remaining = fields.Integer(string='Months Remaining', compute='_compute_months_remaining')
    # method = fields.Selection(selection_add=[('double_declining', 'Double Declining')]
    #                           , ondelete={'double_declining': 'cascade'})
    cut_off_asset_date = fields.Integer(string='Cut Off Asset Date', default=31)
    date_first_depreciation = fields.Selection([
        ('last_day_period', 'Based on Last Day of Purchase Period'),
        ('manual', 'Manual (Defaulted on Purchase Date)')],
        string='Depreciation Dates', default='manual',
        readonly=True, states={'draft': [('readonly', False)]}, required=False, tracking=True,
        help='The way to compute the date of the first depreciation.\n'
             '  * Based on last day of purchase period: The depreciation dates will be based on the last day of the purchase month or the purchase year (depending on the periodicity of the depreciations).\n'
             '  * Based on purchase date: The depreciation dates will be based on the purchase date.')
    
    fiscal_category_id = fields.Many2one('account.asset.category.fiscal', string='Fiscal Asset Category', change_default=True, readonly=True, states={'draft': [('readonly', False)]}, tracking=True)
    method_fiscal = fields.Selection([('linear', 'Straight-line Method'), ('double_declining', 'Declining Balance Method')], string='Computation Method', required=True, readonly=True, states={'draft': [('readonly', False)]}, default='linear',)
    asset_type = fields.Selection([('building', 'Building'), ('non_building', 'Non-Building')], string='Asset type', default='building')
    asset_type_1 = fields.Selection([('non_building', 'Non-Building')], string='Asset type')
    sub_asset_type = fields.Selection([('permanent', 'Permanent'), ('non_permanent', 'Non-Permanent')], default='permanent')
    non_building_type = fields.Selection([('one_four', 'Category 1'), ('two_eight', 'Category 2'), ('three_sixteen', 'Category 3'), ('four_twenty', 'Category 4')])
    is_monthly_depreciation_fiscal = fields.Boolean(string='Monthly Depreciation', tracking=True)
    is_reset_january_fiscal = fields.Boolean(string='Reset on January')
    months_remaining_fiscal = fields.Integer(string='Months Remaining', compute='_compute_months_remaining_fiscal')
    method_number_fiscal = fields.Integer(string='Number of Depreciations', readonly=True, states={'draft': [('readonly', False)]}, default=5, help="The number of depreciations needed to depreciate your asset")
    method_period_fiscal = fields.Integer(string='Number of Months in a Period', required=True, readonly=True, default=12, states={'draft': [('readonly', False)]},
        help="The amount of time between two depreciations, in months")
    method_end_fiscal = fields.Date(string='Ending Date', readonly=True, states={'draft': [('readonly', False)]})
    depreciation_line_ids_fiscal = fields.One2many('account.asset.fiscal.line', 'asset_id', string='Fiscal Depreciation Lines', readonly=True, states={'draft': [('readonly', False)], 'open': [('readonly', False)]})
    asset_history_lines_ids = fields.One2many('asset.asset.revalue', 'asset_id', string='Asset History Lines')
    asset_value_residual = fields.Float(compute='_amount_residual', digits=0, string='Residual Value', tracking=True)
    account_cip_id = fields.Many2one('asset.cip', string='CIP')
    state = fields.Selection([('waiting_for_approve', 'Waiting For Approval'),('draft', 'Draft'), ('open', 'Running'), ('close', 'Close'),('sold', 'Sold'),('reject', 'Reject'),('dispose', 'Dispose')],
        string='Status', required=True, copy=False, default='draft',ondelete={'waiting_for_approve': 'cascade', 'reject': 'cascade'},
        help="When an asset is created, the status is 'Draft'.\n"
             "If the asset is confirmed, the status goes in 'Running' and the depreciation lines can be posted in the accounting.\n"
             "You can manually close an asset when the depreciation is over. If the last line of depreciation is posted, the asset automatically goes in that status.")
     
    state1 = fields.Selection(related="state")
    state2 = fields.Selection(related="state")
    approval_matrix_id = fields.Many2one('assets.approval.matrix', compute="_compute_approval_matrix_id", string="Approval Matrix", store=True)
    approved_matrix_ids = fields.One2many('assets.approval.matrix.line', 'assets_id', compute="_compute_approving_matrix_lines", store=True, string="Approved Matrix")
    is_approval_matrix = fields.Boolean(compute="_compute_approval_matrix", string="Approving Matrix")
    is_approve_button = fields.Boolean(string='Is Approve Button', compute='_get_approve_button', store=False)
    approval_matrix_line_id = fields.Many2one('assets.approval.matrix.line', string='Assets Approval Matrix Line', compute='_get_approve_button', store=False)
    request_partner_id = fields.Many2one('res.partner', string="Requested Partner", tracking=True)
    company_id = fields.Many2one('res.company', string="Company", required=True, tracking=True, readonly=True, default=lambda self: self.env.company.id)
    # branch_id = fields.Many2one('res.branch', string="Branch", required=True, domain="[('company_id', '=', company_id)]", tracking=True, default=lambda self: self.env.user.branch_id.id)
    # branch_id = fields.Many2one(
    #     'res.branch',
    #     required=True,
    #     string="Branch",
    #     tracking=True,
    #     default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False,
    #     readonly=False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    asset_sequence = fields.Char('Sequence', default='New', tracking=True)
    product_id = fields.Many2one('product.product', string="Product", tracking=True)
    fiscal_prorata_temporis = fields.Boolean('Prorata Temporis', tracking=True)
    location = fields.Char('Location', tracking=True)
    po_ref = fields.Char('Purchase Order Reference', tracking=True)
    asset_post_entries_count = fields.Integer(string='Asset Post Entries Count', compute='_compute_asset_post_entries_count')
    asset_dispose_entries_count = fields.Integer(string='Asset Dispose Entries Count', compute='_compute_asset_post_entries_count')
    method_period = fields.Integer(string='Number of Months in a Period', required=True, help="The amount of time between two depreciations, in months")
    method = fields.Selection([('linear', 'Linear'), ('degressive', 'Degressive'),('double_declining', 'Double Declining')], string='Computation Method',
        required=True, tracking=True,
        help="Choose the method to use to compute the amount of depreciation lines.\n  * Linear: Calculated on basis of: Gross Value / Number of Depreciations\n"
             "  * Degressive: Calculated on basis of: Residual Value * Degressive Factor")
    method_time = fields.Selection([('number', 'Number of Entries'), ('end', 'Ending Date')], string='Time Method', required=True,
        related='category_id.method_time', tracking=True,
        help="Choose the method to use to compute the dates and number of entries.\n"
             "  * Number of Entries: Fix the number of entries and the time between 2 depreciations.\n"
             "  * Ending Date: Choose the time between 2 depreciations and the date the depreciations won't go beyond.")
    method_end = fields.Date('Ending date', related='category_id.method_end')
    method_progress_factor = fields.Float(string='Degressive Factor')
    is_revaluation_asset = fields.Boolean(string='Revaluation Asset', default=False)
    is_convert_to_zero = fields.Boolean(string='Convert Residual to Zero',)
    is_include_salvage_value = fields.Boolean(string='Include Salvage Value',)
    first_depreciation_date_fiscal = fields.Date(string='First Depreciation Date Fiscal')
    # equipment_id = fields.Many2one('equipment.equipment', string='Equipment', required=False, ondelete='cascade')
    # show_sale_dispose = fields.Boolean("Show Sale Button",compute='check_equipment_created')
    # show_dispose = fields.Boolean("Show Dispose",compute='check_equipment_created')
    # product_template_id = fields.Many2one('product.template', string='Product Template')
    prorata_type = fields.Selection([
        ('monthly', 'Monthly Prorata'),
        ('daily', 'Daily Prorata')
    ], string='Prorata Type', default='monthly')

            
    @api.onchange('category_id')
    def _onchange_category_id(self):
        for rec in self:
            rec.is_convert_to_zero = rec.category_id.is_convert_to_zero
            rec.is_include_salvage_value = rec.category_id.is_include_salvage_value
            rec.method_period = rec.category_id.method_period
            rec.is_monthly_depreciation = rec.category_id.is_monthly_depreciation
            rec.is_reset_january = rec.category_id.is_reset_january

    @api.onchange('is_monthly_depreciation')
    def onchange_monthly_depreciation(self):
        for rec in self:
            if rec.is_monthly_depreciation == False:
                rec.is_reset_january = False

    def check_equipment_created(self):
        for rec in self:
            equip_ids = self.env['maintenance.equipment'].search([('account_asset_id','=',rec.id)]).ids
            if not equip_ids:
                if rec.state == 'open':
                    rec.show_sale_dispose  = True
                    rec.show_dispose = True
                else:
                    rec.show_sale_dispose = False
                    rec.show_dispose = False
            else:
                rec.show_sale_dispose = False
                rec.show_dispose = False


    def _compute_entries(self, date, group_entries=False):
        depreciation_ids = self.env['account.asset.depreciation.line'].search([
            ('asset_id', 'in', self.ids), ('depreciation_date', '<=', date),
            ('move_id.state', '=', 'draft'),
            ('move_id.period_id', '!=', False)])
        if group_entries:
            return depreciation_ids.create_grouped_move()
        for line in depreciation_ids:
            line.move_id.action_post()
        return depreciation_ids

    # @api.onchange('is_reset_january')
    # def onchange_is_reset_january(self):
    #     if self.is_reset_january == True:
    #         first_depreciation_manual_date = self.date
    #     else:
    #         get_first_day = date_utils.start_of(self.date, 'year')
    #         first_depreciation_manual_date = get_first_day
        


    def _compute_asset_post_entries_count(self):
        sold_moves = self.env['account.move'].search([('account_asset_id', '=', self.id), ('move_type', '=', 'entry'),('account_asset_id.state', '=', 'sold')])
        dispose_moves = self.env['account.move'].search([('account_asset_id', '=', self.id), ('move_type', '=', 'entry'),('account_asset_id.state', '=', 'dispose')])
        for rec in self:
            rec.asset_post_entries_count = len(sold_moves)
            rec.asset_dispose_entries_count = len(dispose_moves)


    def set_to_dispose(self):
        move_ids = self._get_disposal_moves()
        if move_ids:
            self.state = 'dispose'
        return True
    
    def cancel_dispose(self):
        self.state = 'open'
        return True

    def validate_dispose(self):
        move_ids = self._get_disposal_moves()
        if move_ids:
            return self._return_disposal_view(move_ids) 
        # Fallback, as if we just clicked on the smartbutton
        return self.open_entries()


    @api.model
    def get_seq_name(self, vals):
        cat_id = vals['category_id']
        asc_rec = self.env["account.asset.category"].search([("id", "=", cat_id)], limit=1)
        seq_id = self.env["ir.sequence"].search([("id", "=", asc_rec.sequence_id.id)], limit=1)
        # seq_code = asc_rec.name + "/" + str(asc_rec.id)
        seq_code = (asc_rec.name or '') + "/" + str(asc_rec.id)
        seq_id.update({'code': seq_code})
        return self.env["ir.sequence"].next_by_code(seq_code) or "/"

    @api.model
    def create(self, vals):
        if vals.get("asset_sequence", _("New")) == _("New"):
            vals["asset_sequence"] = self.get_seq_name(vals)
        asset = super(Asset, self).create(vals)  
        return asset

    @api.onchange('method_fiscal')
    def onchange_method(self):
        for rec in self:
            if rec.method_fiscal == 'double_declining':
                rec.asset_type = 'non_building'
                rec.asset_type_1 = 'non_building'
            else:
                rec.asset_type_1 = ''

    @api.onchange('asset_type','sub_asset_type','non_building_type')
    def onchange_depreciation(self):
        for rec in self:
            if rec.asset_type == 'building':
                if rec.sub_asset_type == 'permanent':
                    rec.method_number_fiscal = 20
                if rec.sub_asset_type == 'non_permanent':
                    rec.method_number_fiscal = 10
            if rec.asset_type == 'non_building':
                if rec.non_building_type == 'one_four':
                    rec.method_number_fiscal = 4
                if rec.non_building_type == 'two_eight':
                    rec.method_number_fiscal = 8
                if rec.non_building_type == 'three_sixteen':
                    rec.method_number_fiscal = 16
                if rec.non_building_type == 'four_twenty':
                    rec.method_number_fiscal = 20


    @api.depends('approval_matrix_id')
    def _compute_approving_matrix_lines(self):
        for record in self:
            data = []
            counter = 1
            if record.approval_matrix_id and record.approval_matrix_id.assets_approval_matrix_line_ids:
                for line in record.approval_matrix_id.assets_approval_matrix_line_ids:
                    data.append((0, 0, {
                        'sequence' : counter,
                        'user_ids' : [(6, 0, line.user_ids.ids)],
                        'minimum_approver' : line.minimum_approver,
                    }))
                    counter += 1
            record.approved_matrix_ids = data
            
    @api.onchange('name')
    def onchange_name(self):
        self._compute_approval_matrix_id()
        self._compute_approval_matrix()
        
    @api.depends('branch_id')
    def _compute_approval_matrix_id(self):
        is_assets_approving_matrix = self.env['ir.config_parameter'].sudo().get_param('is_assets_approving_matrix', False)
        for record in self:
            record.approval_matrix_id = False
            if record.is_approval_matrix:
                if record.is_approval_matrix:
                    approval_matrix_id = self.env['assets.approval.matrix'].search([
                                ('branch_id', '=', record.branch_id.id),
                                ('company_id', '=', record.company_id.id)], limit=1)
                    record.approval_matrix_id = approval_matrix_id and approval_matrix_id.id or False
    
    @api.model
    def _send_whatsapp_message(self, template_id, approver, url=False, reason=False):
        return True
        for record in self:
            string_test = str(tools.html2plaintext(template_id.body_html))
            if "${approver_name}" in string_test:
                string_test = string_test.replace("${approver_name}", approver.name)
            if "${submitter_name}" in string_test:
                string_test = string_test.replace("${submitter_name}", record.request_partner_id.name)
            if "${name_asset}" in string_test:
                string_test = string_test.replace("${name_asset}", record.name)
            if "${category_id_asset}" in string_test:
                string_test = string_test.replace("${category_id_asset}", str(record.category_id))
            if "${value_asset}" in string_test:
                string_test = string_test.replace("${value_asset}", str(record.value))
            if "${currency_id_asset}" in string_test:
                string_test = string_test.replace("${currency_id_asset}", str(record.currency_id))
            if "${create_date}" in string_test:
                string_test = string_test.replace("${create_date}", fields.Datetime.from_string(
                    record.create_date).strftime('%d/%m/%Y'))
            if "${feedback}" in string_test:
                string_test = string_test.replace("${feedback}", reason)
            if "${br}" in string_test:
                string_test = string_test.replace("${br}", f"\n")
            if "${url}" in string_test:
                string_test = string_test.replace("${url}", url)
            phone_num = str(approver.mobile or approver.mobile_phone)
            if "+" in phone_num:
                phone_num = phone_num.replace("+", "")
            param = {'body': string_test, 'text': string_test, 'phone': phone_num, 'previewBase64': '', 'title': ''}
            domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
            token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
            try:
                request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param, headers=headers, verify=True)
                try:
                    response = json.loads(request_server.text)
                except json.JSONDecodeError as e:
                    _logger.error("Failed to decode JSON response: %s", request_server.text)
                    _logger.exception(e)
                    response = {}
            except requests.ConnectionError as e:
                _logger.error("Connection error: %s", e)
                _logger.exception(e)
                response = {}
            except requests.RequestException as e:
                _logger.error("Request error: %s", e)
                _logger.exception(e)
                response = {}
                
    def _get_approve_button(self):
        for record in self:
            matrix_line = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
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
    
    def _compute_approval_matrix(self):
        is_assets_approving_matrix = self.env['ir.config_parameter'].sudo().get_param('is_assets_approving_matrix', False)
        for record in self:
            record.is_approval_matrix = is_assets_approving_matrix
            
    def action_request_approval(self):
        for record in self:
            action_id = self.env.ref('om_account_asset.action_account_asset_asset_form')
            template_id = self.env.ref('equip3_accounting_asset.email_template_asset_approval_matrix')
            wa_template_id = self.env.ref('equip3_accounting_asset.email_template_req_asset_wa')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=account.asset.asset'
            record.request_partner_id = self.env.user.partner_id.id
            if record.approved_matrix_ids and len(record.approved_matrix_ids[0].user_ids) > 1:
                for approved_matrix_id in record.approved_matrix_ids[0].user_ids:
                    approver = approved_matrix_id
                    ctx = {
                        'email_from' : self.env.user.company_id.email,
                        'email_to' : approver.work_email,
                        'approver_name' : approver.name,
                        'date': date.today(),
                        'submitter' : self.env.user.name,
                        'url' : url,
                        "name_asset": record.name,
                        "category_id_asset": record.category_id.name,
                        "value_asset": record.value,
                        "currency_id_asset": record.currency_id.name,
                    }
                    template_id.with_context(ctx).send_mail(record.id, True)
                    # record._send_whatsapp_message(wa_template_id, approver, url)
            else:
                approver = record.approved_matrix_ids[0].user_ids[0]
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : approver.work_email,
                    'approver_name' : approver.name,
                    'date': date.today(),
                    'submitter' : self.env.user.name,
                    'url' : url,
                    "name_asset": record.name,
                    "category_id_asset": record.category_id.name,
                    "value_asset": record.value,
                    "currency_id_asset": record.currency_id.name,
                }
                template_id.with_context(ctx).send_mail(record.id, True)
                # record._send_whatsapp_message(wa_template_id, approver, url)
            record.write({'state' : 'waiting_for_approve'})
    
    def action_approve(self):
        for record in self:
            action_id = self.env.ref('om_account_asset.action_account_asset_asset_form')
            template_id = self.env.ref('equip3_accounting_asset.email_template_asset_approval_matrix')
            template_id_submitter = self.env.ref('equip3_accounting_asset.email_template_asset_submitter_approval_matrix')
            wa_template_id = self.env.ref('equip3_accounting_asset.email_template_req_asset_wa')
            wa_template_submitted = self.env.ref('equip3_accounting_asset.email_template_appr_asset_wa')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=account.asset.asset'
            user = self.env.user
            if record.is_approve_button and record.approval_matrix_line_id:
                approval_matrix_line_id = record.approval_matrix_line_id
                if user.id in approval_matrix_line_id.user_ids.ids and \
                    user.id not in approval_matrix_line_id.approved_users.ids:
                    name = approval_matrix_line_id.state_char or ''
                    if name != '':
                        name += "\n • %s: Approved" % (self.env.user.name)
                    else:
                        name += "• %s: Approved" % (self.env.user.name)

                    approval_matrix_line_id.write({
                        'last_approved': self.env.user.id, 'state_char': name,
                        'approved_users': [(4, user.id)]})
                    if approval_matrix_line_id.minimum_approver == len(approval_matrix_line_id.approved_users.ids):
                        approval_matrix_line_id.write({'time_stamp': datetime.now(), 'approved': True})
                        ctx = {
                            'email_from' : self.env.user.company_id.email,
                            'email_to' : record.request_partner_id.email,
                            'approver_name' : record.name,
                            'date': date.today(),
                            'create_date': record.create_date.date(),
                            'submitter' : self.env.user.name,
                            'url' : url,
                            "name_asset": record.name,
                            "category_id_asset": record.category_id.name,
                            "value_asset": record.value,
                            "currency_id_asset": record.currency_id.name,
                        }
                        template_id_submitter.sudo().with_context(ctx).send_mail(record.id, True)
                        # record._send_whatsapp_message(wa_template_submitted, record.request_partner_id.user_ids, url)
                        next_approval_matrix_line_id = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
                        if next_approval_matrix_line_id and len(next_approval_matrix_line_id[0].user_ids) > 1:
                            for approving_matrix_line_user in next_approval_matrix_line_id[0].user_ids:
                                ctx = {
                                    'email_from' : self.env.user.company_id.email,
                                    'email_to' : approving_matrix_line_user.partner_id.email,
                                    'approver_name' : approving_matrix_line_user.name,
                                    'date': date.today(),
                                    'submitter' : self.env.user.name,
                                    'url' : url,
                                    "name_asset": record.name,
                                    "category_id_asset": record.category_id.name,
                                    "value_asset": record.value,
                                    "currency_id_asset": record.currency_id.name,
                                }
                                template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                # record._send_whatsapp_message(wa_template_id, approving_matrix_line_user, url)
                        else:
                            if next_approval_matrix_line_id and next_approval_matrix_line_id[0].user_ids:
                                ctx = {
                                    'email_from' : self.env.user.company_id.email,
                                    'email_to' : next_approval_matrix_line_id[0].user_ids[0].partner_id.email,
                                    'approver_name' : next_approval_matrix_line_id[0].user_ids[0].name,
                                    'date': date.today(),
                                    'submitter' : self.env.user.name,
                                    'url' : url,
                                    "name_asset": record.name,
                                    "category_id_asset": record.category_id.name,
                                    "value_asset": record.value,
                                    "currency_id_asset": record.currency_id.name,
                                }
                                template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                # record._send_whatsapp_message(wa_template_id, next_approval_matrix_line_id[0].user_ids[0], url)
            if len(record.approved_matrix_ids) == len(record.approved_matrix_ids.filtered(lambda r:r.approved)):
                record.validate()
                
    
    def action_reject(self):
        return {
                'type': 'ir.actions.act_window',
                'name': 'Rejected Reason',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'assets.approval.reject',
                'target': 'new',
            }

    def open_asset_post_entries(self):
        moves = self.env['account.move'].search([('account_asset_id', '=', self.id), ('move_type', '=', 'entry'), ('account_asset_id.state', '=', 'sold')])
        
        # asset_sale = self.env['account.asset.sale'].search([('asset_id', '=', self.id)])
        amount_total = 0
        for move in moves:
            for line in move.line_ids:
                amount_total += line.debit

            move.amount_untaxed = amount_total
            move.amount_total = amount_total
            
        return {
            'name': _('Journal Entries'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', moves.ids)],
        }
    
    def open_asset_dispose_entries(self):
        moves = self.env['account.move'].search([('account_asset_id', '=', self.id), ('move_type', '=', 'entry'), ('account_asset_id.state', '=', 'dispose')])
        
        for move in moves:
            for asset in self:
                # Assuming asset_value_residual is a float or can be converted to a float
                try:
                    asset_value_residual = float(asset.asset_value_residual)
                except ValueError:
                    asset_value_residual = 0.0  # Handle invalid values gracefully

                # # Calculate amount_untaxed and amount_total based on asset_value_residual
                # amount_untaxed = asset_value_residual * 0.9  # Example calculation
                # amount_total = asset_value_residual * 1.1    # Example calculation

                # Write the calculated values to the appropriate fields
                move.amount_untaxed = asset_value_residual
                move.amount_total = asset_value_residual

        return {
            'name': _('Journal Entries'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', moves.ids)],
        }

    def open_asset_invoices(self):
        moves = self.env['account.move'].search([('account_asset_id', '=', self.id), ('move_type', '=', 'out_invoice')])
        return {
            'name': _('Invoices'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', moves.ids)],
        }

    @api.onchange('fiscal_category_id')
    def onchange_fiscal_category_id_id(self):
        vals = self.onchange_fiscal_category_id_values(self.fiscal_category_id.id)
        # We cannot use 'write' on an object that doesn't exist yet
        if vals:
            for k, v in vals['value'].items():
                setattr(self, k, v)

    def onchange_fiscal_category_id_values(self, fiscal_category_id):
        if fiscal_category_id:
            fiscal_category = self.env['account.asset.category.fiscal'].browse(fiscal_category_id)
            return {
                'value': {
                    'method_fiscal': fiscal_category.method,
                    'method_number_fiscal': fiscal_category.method_number,
                    'method_period_fiscal': fiscal_category.method_period,
                    'is_monthly_depreciation_fiscal' : fiscal_category.is_monthly_depreciation,
                    'is_reset_january_fiscal' : fiscal_category.is_reset_january,
                    'asset_type' : fiscal_category.asset_type,
                    'sub_asset_type' : fiscal_category.sub_asset_type,
                    'non_building_type' : fiscal_category.non_building_type,
                    'fiscal_prorata_temporis': fiscal_category.prorata
                }
            }
         
    def _compute_months_remaining_fiscal(self):
        fiscal_depreciation_lines = self.env['account.asset.fiscal.line'].search([('asset_id', '=', self.id)], order='depreciation_date_fiscal desc', limit=1)

        if len(fiscal_depreciation_lines) > 0:
            fiscal_depreciation_date = fiscal_depreciation_lines.depreciation_date_fiscal
            self.months_remaining_fiscal = 12 - fiscal_depreciation_date.month
        else:
            self.months_remaining_fiscal = 0
            
  
    @api.onchange('category_id')
    def onchange_category_id(self):
        vals = self.onchange_category_id_values(self.category_id.id)
        # We cannot use 'write' on an object that doesn't exist yet
        if vals:
            for k, v in vals['value'].items():
                setattr(self, k, v)         
    
    
    def onchange_category_id_values(self, category_id):
        if category_id:
            category = self.env['account.asset.category'].browse(category_id)
            vals = {
                    'method': category.method,
                    'method_number': category.method_number,
                    'method_time': category.method_time,
                    'method_period': category.method_period,
                    'method_progress_factor': category.method_progress_factor,
                    'method_end': category.method_end,
                    'prorata': category.prorata,
                    'prorata_type': category.prorata_type,
                    'date_first_depreciation': category.date_first_depreciation,
                    'account_analytic_id': category.account_analytic_id.id,
                    'analytic_tag_ids': [(6, 0, category.analytic_tag_ids.ids)],
                    'cut_off_asset_date' : category.cut_off_asset_date,
                }
                
            if category.method == 'double_declining':
                vals.update({
                    'is_monthly_depreciation' : category.is_monthly_depreciation,
                    'is_reset_january' : category.is_reset_january,
                    })
                    
            return {'value': vals}

         
    @api.onchange('cut_off_asset_date','prorata','date')
    def onchange_cut_off_asset_date(self):
        if self.cut_off_asset_date < 1 or self.cut_off_asset_date > 31:
            raise ValidationError(_('Fill in the Cut off Asset Date with a value between the 1st to 31st.'))
        date = self.date
        if date:
            date_list = str(date).split('-')
            cut_off_date_str = len(str(self.cut_off_asset_date))>=2 and str(self.cut_off_asset_date) or '0' + str(self.cut_off_asset_date)
            cut_off_date = '%s-%s-%s'%(date_list[0], date_list[1], cut_off_date_str)
            if not self.prorata and str(date) > cut_off_date:
                month = (int(date_list[1]) < 10 and '0%s'%(int(date_list[1])+1))\
                        or (int(date_list[1]) >= 10 and int(date_list[1]) < 12 and str(int(date_list[1])+1))\
                        or '01'
                year = int(date_list[1]) < 12 and str(int(date_list[0])) or str(int(date_list[0])+1)
                self.first_depreciation_manual_date = '%s-%s-%s'%(year, month, '01')
                # self.first_depreciation_manual_date = self.first_depreciation_manual_date + relativedelta(day=31)
            elif not self.prorata and str(date) <= cut_off_date:
                self.first_depreciation_manual_date = '%s-%s-%s'%(date_list[0], date_list[1], '01')
                # self.first_depreciation_manual_date = self.first_depreciation_manual_date + relativedelta(day=31)
            else:
                self.first_depreciation_manual_date = date 
                
                
                
    # @api.onchange('cut_off_asset_date')
    # def _onchange_cut_off_asset_date(self):
    #     if self.cut_off_asset_date < 1 or self.cut_off_asset_date > 31:
    #         raise ValidationError(_('Fill in the Cut off Asset Date with a value between the 1st to 31st.'))
        
        
    @api.constrains('cut_off_asset_date')
    def _check_cut_off_asset_date(self):
        if self.cut_off_asset_date < 1 or self.cut_off_asset_date > 31:
            raise ValidationError(_('Fill in the Cut off Asset Date with a value between the 1st to 31st.'))



    def _compute_board_amount(self, sequence, residual_amount, amount_to_depr, salvage_value, undone_dotation_number, posted_depreciation_line_ids, total_days, depreciation_date):
        # amount = super(Asset, self)._compute_board_amount(sequence, residual_amount, amount_to_depr, salvage_value, undone_dotation_number, posted_depreciation_line_ids, total_days, depreciation_date)
        if sequence == undone_dotation_number:
            amount = residual_amount
            if self.method == 'linear':
                if self.is_include_salvage_value:
                    # amount = (amount_to_depr - salvage_value) / (undone_dotation_number - len(posted_depreciation_line_ids))
                    amount = (amount_to_depr - salvage_value) / self.method_number
                    if self.prorata and self.prorata_type == 'daily':
                        date = depreciation_date
                        if self.method_period % 12 != 0:
                            month_days = calendar.monthrange(date.year, date.month)[1]
                            days = month_days - date.day + 1
                        else:
                            # days = (self.first_depreciation_manual_date.replace(year=date.year) - date).days + 1
                            days = (self.first_depreciation_manual_date - date.replace(year=self.first_depreciation_manual_date.year)).days
                        amount = (amount_to_depr - salvage_value) / self.method_number * (days / total_days)
                    elif self.prorata and self.prorata_type == 'monthly':
                        remaining_month = self.first_depreciation_manual_date.month - depreciation_date.month
                        amount = (amount_to_depr - salvage_value) / self.method_number * (remaining_month / 12)
                # else:
                    # amount = (amount_to_depr - salvage_value) / (undone_dotation_number - len(posted_depreciation_line_ids))
            if self.method == 'double_declining':
                amount = (100 / undone_dotation_number * 2) * (residual_amount - self.salvage_value) / 100
                if self.is_include_salvage_value and not self.is_convert_to_zero:
                    amount = (100 / undone_dotation_number * 2) * (residual_amount - self.salvage_value) / 100
                if not self.is_include_salvage_value and self.is_convert_to_zero:
                    amount = residual_amount - salvage_value
                if self.is_include_salvage_value and self.is_convert_to_zero:
                    amount = residual_amount - salvage_value
                if self.prorata and self.prorata_type == 'daily':
                    if self.is_convert_to_zero:
                        amount = residual_amount - salvage_value
                    else:
                        date = depreciation_date
                        if self.method_period % 12 != 0:
                            month_days = calendar.monthrange(date.year, date.month)[1]
                            days = month_days - date.day + 1
                        else:
                            # days = (self.first_depreciation_manual_date.replace(year=date.year) - date).days + 1
                            days = (self.first_depreciation_manual_date - date.replace(year=self.first_depreciation_manual_date.year)).days
                        amount = (100 / self.method_number * 2) * (residual_amount - salvage_value) * (days / total_days) / 100
                # if not self.is_convert_to_zero:
                    # amount = (residual_amount / undone_dotation_number) * 2
                if self.prorata and self.prorata_type == 'monthly':
                    if self.is_convert_to_zero:
                        amount = residual_amount - salvage_value
                    else:
                        remaining_month = self.first_depreciation_manual_date.month - depreciation_date.month
                        amount = (100 / self.method_number * 2) * (residual_amount - salvage_value) * (remaining_month / 12) / 100
                     
            if self.method == 'degressive':
                amount = self.method_progress_factor * (residual_amount - salvage_value)
                if self.is_include_salvage_value and not self.is_convert_to_zero:
                    amount = self.method_progress_factor * (residual_amount - salvage_value)
                if not self.is_include_salvage_value and self.is_convert_to_zero:
                    amount = residual_amount - salvage_value
                if self.is_include_salvage_value and self.is_convert_to_zero:
                    amount = residual_amount - salvage_value
                if self.prorata and self.prorata_type == 'daily':
                    if self.is_convert_to_zero:
                        amount = residual_amount - salvage_value
                    else:
                        date = depreciation_date
                        if self.method_period % 12 != 0:
                            month_days = calendar.monthrange(date.year, date.month)[1]
                            days = month_days - date.day + 1
                        else:
                            # days = (self.first_depreciation_manual_date.replace(year=date.year) - date).days + 1
                            days = (self.first_depreciation_manual_date - date.replace(year=self.first_depreciation_manual_date.year)).days
                        amount = self.method_progress_factor * (residual_amount - salvage_value) * (days / total_days)
                # if not self.is_convert_to_zero:
                #     amount = residual_amount * self.method_progress_factor
                if self.prorata and self.prorata_type == 'monthly':
                    if self.is_convert_to_zero:
                        amount = residual_amount - salvage_value
                    else:
                        remaining_month = self.first_depreciation_manual_date.month - depreciation_date.month
                        amount = self.method_progress_factor * (residual_amount - salvage_value) * (remaining_month / 12)

        else:
            if self.method == 'linear':
                amount = (amount_to_depr - salvage_value) / (undone_dotation_number - len(posted_depreciation_line_ids))
                if self.prorata and self.prorata_type == 'daily':
                    amount = (amount_to_depr - salvage_value) / self.method_number
                    if sequence == 1:
                        date = self.first_depreciation_manual_date
                        if self.method_period % 12 != 0:
                            month_days = calendar.monthrange(date.year, date.month)[1]
                            days = month_days - date.day + 1
                        else:
                            days = (self.company_id.compute_fiscalyear_dates(date)['date_to'] - date).days + 1
                        amount *= (days / total_days)
                elif self.prorata and self.prorata_type == 'monthly':
                    amount = (amount_to_depr - salvage_value) / self.method_number
                    if sequence == 1:
                        remaining_month = 12 - self.first_depreciation_manual_date.month + 1
                        amount *= (remaining_month / 12)
            
            if self.method == 'double_declining':
                if self.is_reset_january and sequence == 1 and depreciation_date.month != 1:
                    months_remaining = 12 + 1 - depreciation_date.month
                    amount = (1/(undone_dotation_number-1))*(2*residual_amount)*((months_remaining)/12)
                elif self.is_reset_january and depreciation_date.month != 1:
                    amount = (residual_amount / (undone_dotation_number-1)) * 2
                elif self.prorata and self.prorata_type == 'daily':
                    amount = (100 / self.method_number * 2) * (residual_amount - salvage_value) / 100
                    if sequence == 1:
                        date = depreciation_date
                        if self.method_period % 12 != 0:
                            month_days = calendar.monthrange(date.year, date.month)[1]
                            days = month_days - date.day + 1
                        else:
                            days = (self.company_id.compute_fiscalyear_dates(date)['date_to'] - date).days + 1
                        amount *= (days / total_days)
                elif self.prorata and self.prorata_type == 'monthly':
                    amount = (100 / self.method_number * 2) * (residual_amount - salvage_value) / 100
                    if sequence == 1:
                        remaining_month = 12 - self.first_depreciation_manual_date.month + 1
                        amount *= (remaining_month / 12)
                else:
                    # amount = (residual_amount / undone_dotation_number) * 
                    amount = (100 / undone_dotation_number * 2) * (residual_amount - self.salvage_value) / 100
            
            elif self.method == 'degressive':
                # amount = residual_amount * self.method_progress_factor
                amount = self.method_progress_factor * (residual_amount - salvage_value)
                if self.prorata and self.prorata_type == 'daily':
                    if sequence == 1:
                        date = self.first_depreciation_manual_date
                        if self.method_period % 12 != 0:
                            month_days = calendar.monthrange(date.year, date.month)[1]
                            days = month_days - date.day + 1
                        else:
                            days = (self.company_id.compute_fiscalyear_dates(date)['date_to'] - date).days + 1
                        amount *= (days / total_days)
                elif self.prorata and self.prorata_type == 'monthly':
                    if sequence == 1:
                        remaining_month = 12 - self.first_depreciation_manual_date.month + 1
                        amount *= (remaining_month / 12)
        return amount
    
    
    def _compute_board_amount_fiscal(self, sequence, residual_amount, amount_to_depr, fiscal_undone_dotation_number, depreciation_line_ids_fiscal, total_days, depreciation_date,end_month_dep):
        amount = 0
        if sequence == fiscal_undone_dotation_number:
            amount = residual_amount
            if self.method_fiscal == 'linear':
                if self.salvage_value > 0:
                    amount = round((amount_to_depr - self.salvage_value) / (fiscal_undone_dotation_number - len(depreciation_line_ids_fiscal)), 2)
            if self.method_fiscal == 'double_declining':
                if self.method_number_fiscal == 4:
                    p = 0.5  # 50%
                elif self.method_number_fiscal == 8:
                    p = 0.25  # 25%
                elif self.method_number_fiscal == 16:
                    p = 0.125  # 12.50%
                elif self.method_number_fiscal == 20:
                    p = 0.1  # 10%
                else:
                    p = 0
        
                if self.is_reset_january_fiscal :
                    amount = (residual_amount * p) * (end_month_dep.month / 12)
                else:
                    amount = (residual_amount * p)
                
        else:
            if self.method_fiscal == 'linear':
                amount = round((amount_to_depr - self.salvage_value) / (fiscal_undone_dotation_number - len(depreciation_line_ids_fiscal)), 2)
                # if self.salvage_value > 0:
                #     amount = round((amount_to_depr - self.salvage_value) / (fiscal_undone_dotation_number - len(depreciation_line_ids_fiscal)), 2)
            elif self.method_fiscal == 'double_declining':
                if self.method_number_fiscal == 4:
                    p = 0.5  # 50%
                elif self.method_number_fiscal == 8:
                    p = 0.25  # 25%
                elif self.method_number_fiscal == 16:
                    p = 0.125  # 12.50%
                elif self.method_number_fiscal == 20:
                    p = 0.1  # 10%
                else:
                    p = 0
                if self.is_reset_january_fiscal and sequence == 1:
                    months_remaining_fiscal = 12 - (depreciation_date.month - 1)
                    # amount = (1/fiscal_undone_dotation_number)*(2*residual_amount)*((months_remaining_fiscal+1)/12)
                    amount = (residual_amount * p) * (months_remaining_fiscal / 12)
                elif self.is_reset_january_fiscal:
                    amount = (residual_amount * p)
                else:
                    amount = (residual_amount / fiscal_undone_dotation_number) * 2
                    

        return amount
    
    @api.depends('value', 'salvage_value', 'depreciation_line_ids.move_check', 'depreciation_line_ids.amount')
    def _amount_residual(self):
        res = super(Asset, self)._amount_residual()
        for rec in self:
            # last_depreciation_line = rec.depreciation_line_ids.filtered(lambda r: r.move_id == False or r.move_id.state != 'posted')[-1]
            # rec.asset_value_residual = sum(rec.depreciation_line_ids.filtered(lambda r: r.move_id == False or r.move_id.state != 'posted').mapped('amount')) + last_depreciation_line.remaining_value
            rec.asset_value_residual = rec.value - sum(rec.depreciation_line_ids.filtered(lambda r: r.move_id.state == 'posted').mapped('amount'))
        return res
    

    def compute_fiscal_depreciation(self):
        self.ensure_one()

        depreciation_line_ids_fiscal = []
        commands = []
        if self.depreciation_line_ids_fiscal:
            commands = [(5,0,0)]
        
        if self.value_residual != 0.0:
            amount_to_depr = residual_amount = self.value_residual
            get_first_day = date_utils.start_of(self.date, 'year')
            # depreciation_date computed from the purchase date
            depreciation_date = self.first_depreciation_manual_date if not self.is_reset_january_fiscal else get_first_day
            # if self.first_depreciation_manual_date and self.first_depreciation_manual_date != self.date:
            if self.first_depreciation_date_fiscal:

                # depreciation_date set manually from the 'first_depreciation_manual_date' field
                # asset first_depreciation_manual_date is 16 or more, then the depreciation will be on the next month
                # valid_date = int(self.first_depreciation_date_fiscal.strftime("%d"))
                # valid_date = int(get_first_day.strftime("%d"))
                # if 1 <= valid_date <= 15:
                #     if self.is_reset_january_fiscal:
                #         depreciation_date = self.first_depreciation_date_fiscal
                #     else:
                #         depreciation_date = get_first_day

                # else:
                #     if self.is_reset_january_fiscal:
                #         next_month = date_utils.add(self.first_depreciation_date_fiscal, months=1)
                #         date_min = date_utils.start_of(next_month, "month")
                #         depreciation_date = date_min
                #     else:
                #         depreciation_date = get_first_day

                if self.is_reset_january_fiscal:
                    depreciation_date = get_first_day
                else:
                    depreciation_date = self.first_depreciation_date_fiscal

            total_days = (depreciation_date.year % 4) and 365 or 366
            current_amount = 0
            fiscal_undone_dotation_number = self.method_number_fiscal
            if self.method_fiscal == 'linear':
                if self.is_monthly_depreciation_fiscal:
                    fiscal_undone_dotation_number = self.method_number_fiscal * 12
                
            # if self.fiscal_prorata_temporis and self.method_fiscal == 'linear':
            #     fiscal_undone_dotation_number = self.method_number_fiscal + 1
            # else:
            #     if self.method_fiscal == 'double_declining' and self.is_reset_january_fiscal :
            #         fiscal_undone_dotation_number = self.method_number_fiscal + 1
            #     else:
            #         fiscal_undone_dotation_number = self.method_number_fiscal

            _logger.exception(_("Debug: %s", range(len(depreciation_line_ids_fiscal), fiscal_undone_dotation_number)))
            cum = 0
            double_residual_a = 0

            start_month_dep = self.first_depreciation_manual_date
            total_year_dep = self.method_number_fiscal
            total_month_dep = 12 * self.method_number_fiscal
            end_month_dep = start_month_dep + relativedelta(months=total_month_dep -1)


            cum_value = 0
            for x in range(len(depreciation_line_ids_fiscal), fiscal_undone_dotation_number):
                sequence = x + 1
                amount = self._compute_board_amount_fiscal(sequence, residual_amount, amount_to_depr,
                                                    fiscal_undone_dotation_number, depreciation_line_ids_fiscal,
                                                    total_days, depreciation_date,end_month_dep)
                # amount = self.currency_id.round(amount)

                # Convert amount to Decimal and round up to 2 decimal places
                # amount = Decimal(amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                # precision_rounding = Decimal(self.currency_id.rounding)

                # Example of using float_is_zero with Decimal
                # if float_is_zero(amount, precision_rounding=precision_rounding):
                    # pass

                if float_is_zero(amount, precision_rounding=self.currency_id.rounding):
                    continue

                residual_amount -= amount

                # Ensure both are of the same type before subtraction
                # if isinstance(residual_amount, float) and isinstance(amount, Decimal):
                #     residual_amount -= float(amount)
                # elif isinstance(residual_amount, Decimal) and isinstance(amount, float):
                #     residual_amount -= Decimal(amount)
                # else:
                #     residual_amount -= amount
                    
                # type 1
                # if self.method_fiscal == 'double_declining' and not self.is_monthly_depreciation_fiscal:
                if self.method_fiscal == 'double_declining':
                    if self.method_number_fiscal == 4:
                        p = 0.5  # 50%
                    elif self.method_number_fiscal == 8:
                        p = 0.25  # 25%
                    elif self.method_number_fiscal == 16:
                        p = 0.125  # 12.50%
                    elif self.method_number_fiscal == 20:
                        p = 0.1  # 10%
                    else:
                        p = 0

                    if self.fiscal_prorata_temporis:
                        valid_month = int(self.first_depreciation_manual_date.strftime("%m"))
                        if self.first_depreciation_date_fiscal:
                            valid_month = int(self.first_depreciation_date_fiscal.strftime("%m"))
                        dep_month = (12 - valid_month) + 1
                        next_dep_count = valid_month -1
                        depreciation_date = depreciation_date.replace(day=31, month=12)
                        m = (fiscal_undone_dotation_number - 1)
                        if x == 0.0:
                            dep_value = (self.value * p) * (dep_month / 12)
                            cum_value = dep_value
                            res_value = self.value - cum_value
                            #assign to variables
                            cum = (self.value * p)
                            rv = self.value - cum
                            double_residual_a = self.value * p
                        elif m == x:
                            double_dep_value = self.value - cum
                            # dep_value = (double_residual_a * next_dep_count /12) + (double_dep_value * dep_month /12)
                            dep_value = res_value * p
                            cum_value = dep_value + cum_value
                            res_value = self.value - cum_value
                            sub_double_dep_result = self.sub_double_dep_adding(self, res_value, sequence, cum_value, depreciation_date, next_dep_count, p)
                            commands += sub_double_dep_result
                        # elif sequence == fiscal_undone_dotation_number:
                        #     dep_value = res_value * next_dep_count /12
                        #     cum_value = dep_value + cum_value
                        #     res_value = self.value - cum_value
                        else:
                            resid_value = self.value if cum == 0 else rv
                            double_dep_value = resid_value * p
                            double_cum_value = double_dep_value + cum
                            double_res_value = self.value - double_cum_value
                            dep_value = (double_residual_a * next_dep_count /12) + (double_dep_value * dep_month /12)


                            cum_value = dep_value + cum_value
                            res_value = self.value - cum_value
                            double_residual_a = double_dep_value
                            cum = double_cum_value
                            rv = double_res_value
                    else:
                        m = (fiscal_undone_dotation_number - 1)
                        if int(m) == int(x):
                            if self.is_reset_january_fiscal:
                                dep_value = amount
                                cum_value = dep_value + cum 
                                res_value = self.value - cum_value
                            else:
                                # dep_value = residual_amount
                                dep_value = (self.value - cum) * p
                                # cum_value = self.value - residual_amount
                                cum_value = dep_value + cum
                                res_value = self.value - cum_value

                        else:
                            if self.is_reset_january_fiscal:
                                dep_value = amount
                                cum_value = amount + cum
                                res_value = self.value - cum_value
                            else:
                                if self.is_monthly_depreciation_fiscal:
                                    if sequence == 1:
                                        resid_value = self.value if cum == 0 else rv
                                        dep_value = resid_value * p
                                        cum_value = dep_value + cum
                                        res_value = self.value - cum_value
                                        cum = cum_value
                                        rv = res_value
                                else :
                                    resid_value = self.value if cum == 0 else rv
                                    dep_value = resid_value * p
                                    cum_value = dep_value + cum
                                    res_value = self.value - cum_value
                                    cum = cum_value
                                    rv = res_value

                    # type 3
                if self.method_fiscal == 'linear':
                    if self.asset_type == 'non_building':
                        if self.method_number_fiscal == 4:
                            p = 0.25  # 25%
                        elif self.method_number_fiscal == 8:
                            p = 0.125  # 12.50%
                        elif self.method_number_fiscal == 16:
                            p = 0.0625  # 6.25%
                        elif self.method_number_fiscal == 20:
                            p = 0.05  # 5%
                        else:
                            p = 0
                    if self.asset_type == 'building':
                        if self.method_number_fiscal == 20:
                            p = 0.1  # 10%
                        elif self.method_number_fiscal == 10:
                            p = 0.05  # 5%
                        else:
                            p = 0
                    if self.fiscal_prorata_temporis:
                        valid_month = int(self.first_depreciation_date_fiscal.strftime("%m"))
                        dep_month = (12 - valid_month) + 1
                        depreciation_date = depreciation_date.replace(day=31, month=12)
                        m = (fiscal_undone_dotation_number - 1)
                        if int(x) == 0.0:
                            type3_dep_value = (self.value * p) * (dep_month / 12)
                            type3_cum_value = type3_dep_value
                            cum = type3_cum_value
                            type3_res_value = self.value - type3_cum_value
                        elif int(m) == int(x):
                            type3_dep_value = self.value - cum
                            type3_cum_value = self.value
                            type3_res_value = self.value - type3_cum_value
                        else:
                            type3_dep_value = self.value * p
                            type3_cum_value = type3_dep_value + cum
                            cum = type3_cum_value
                            type3_res_value = self.value - type3_cum_value
                    else:
                        # type3_dep_value = self.value * p
                        type3_dep_value = amount
                        type3_cum_value = type3_dep_value + cum
                        cum = type3_cum_value
                        type3_res_value = self.value - type3_cum_value
                        if sequence == fiscal_undone_dotation_number:
                            type3_res_value = round(type3_res_value, 0)

                        # if isinstance(type3_dep_value, float) and isinstance(cum, Decimal):
                        #     type3_cum_value = type3_dep_value + float(cum)
                        # elif isinstance(type3_dep_value, Decimal) and isinstance(cum, float):
                        #     type3_cum_value = Decimal(type3_dep_value) + cum
                        # else:
                        #     type3_cum_value = type3_dep_value + cum

                        # if isinstance(self.value, float) and isinstance(type3_cum_value, Decimal):
                        #     type3_res_value = self.value - float(type3_cum_value)
                        # elif isinstance(self.value, Decimal) and isinstance(type3_cum_value, float):
                        #     type3_res_value = float(self.value) - type3_cum_value
                        # else:
                        #     type3_res_value = self.value - type3_cum_value
                
                if self.method_fiscal == 'double_declining' and self.is_monthly_depreciation_fiscal:
                    if self.is_reset_january_fiscal:
                        start_month = depreciation_date.month - 1
                        end_month = 12
                        if sequence == fiscal_undone_dotation_number:
                            end_month = end_month_dep.month
                        for i in range(start_month if x == 0 else 0, end_month):
                            months_remaining_fiscal = 12 - start_month
                            if sequence == 1:
                                amt = (amount / months_remaining_fiscal)
                                current_amount = current_amount + amt
                            else:
                                amt = (amount / 12)
                                current_amount = current_amount + amt   

                            vals = {
                                'amount_fiscal': amt,
                                'asset_id': self.id,
                                'sequence': sequence,
                                'name': (self.code or '') + '/' + str(sequence),
                                'remaining_value_fiscal': self.value - current_amount,
                                'depreciated_value_fiscal': current_amount,
                                'depreciation_date_fiscal': date(depreciation_date.year, i + 1, 1),
                            }
                            commands.append((0, 0, vals))
                    else :
                        start_month = 0
                        if sequence == 1:
                            # start_month = depreciation_date.month - 1
                            dc_depreciation_date = depreciation_date + relativedelta(months=-1)

                        for i in range(start_month if x == 0 else 0, 12):
                            amt = (amount / 12)
                            amt_fiscal = (resid_value * p) / 12
                            current_amount = current_amount + amt_fiscal
                            # cum_value = cum_value + amt_fiscal
                            dc_depreciation_date += relativedelta(months=+1)
                            vals = {
                                'amount_fiscal': amt_fiscal,
                                'asset_id': self.id,
                                'sequence': sequence,
                                'name': (self.code or '') + '/' + str(sequence),
                                'remaining_value_fiscal': resid_value - amt_fiscal,
                                'depreciated_value_fiscal': current_amount,
                                # 'depreciation_date_fiscal': date(depreciation_date.year, i + 1, 1),
                                'depreciation_date_fiscal': dc_depreciation_date,
                            }
                            commands.append((0, 0, vals)) 
                            resid_value -= amt_fiscal
                            

                elif self.method_fiscal == 'double_declining' and not self.is_monthly_depreciation_fiscal:
                    if self.is_reset_january_fiscal:
                        vals = {
                            'amount_fiscal': dep_value,
                            'asset_id': self.id,
                            'sequence': sequence,
                            'name': (self.code or '') + '/' + str(sequence),
                            'depreciated_value_fiscal': cum_value,
                            'remaining_value_fiscal': res_value,
                            'depreciation_date_fiscal': depreciation_date,
                        }
                        commands.append((0, 0, vals))
                    else:
                        vals = {
                            'amount_fiscal': dep_value,
                            'asset_id': self.id,
                            'sequence': sequence,
                            'name': (self.code or '') + '/' + str(sequence),
                            'depreciated_value_fiscal': cum_value,
                            'remaining_value_fiscal': res_value,
                            'depreciation_date_fiscal': depreciation_date,
                        }
                        commands.append((0, 0, vals))

                # elif self.method == 'double_declining' and self.is_monthly_depreciation:
                #     if self.is_reset_january:
                #         commands = self.calculate_double_declining_reset_january_fiscal(self, commands, sequence, depreciation_date, amount, cum_value, res_value)
                #     else:
                #         commands = self.calculate_double_declining_fiscal(self, commands, sequence, depreciation_date, amount, cum_value, res_value)
                
                if self.method_fiscal == 'linear' and self.is_monthly_depreciation_fiscal:
                    vals = {
                        'amount_fiscal': type3_dep_value,
                        'asset_id': self.id,
                        'sequence': sequence,
                        'name': (self.code or '') + '/' + str(sequence),
                        'depreciated_value_fiscal': type3_cum_value,
                        'remaining_value_fiscal': type3_res_value,
                        # 'remaining_value_fiscal': round(type3_res_value, 0) if sequence != fiscal_undone_dotation_number else self.salvage_value,
                        'depreciation_date_fiscal': depreciation_date,
                    }
                    commands.append((0, 0, vals))
                elif self.method_fiscal == 'linear' and not self.is_monthly_depreciation_fiscal:
                    vals = {
                        'amount_fiscal': type3_dep_value,
                        'asset_id': self.id,
                        'sequence': sequence,
                        'name': (self.code or '') + '/' + str(sequence),
                        'depreciated_value_fiscal': type3_cum_value,
                        'remaining_value_fiscal': round(type3_res_value, 0),
                        'depreciation_date_fiscal': depreciation_date,
                    }
                    commands.append((0, 0, vals))
                # depreciation_date = depreciation_date + relativedelta(months=+self.method_period_fiscal)

                if(self.is_monthly_depreciation_fiscal):
                    # depreciation_date = depreciation_date + relativedelta(months=+self.method_period_fiscal)
                    depreciation_date = depreciation_date + relativedelta(months=+1)
                else:
                    depreciation_date = depreciation_date + relativedelta(years=+1)
                    # cum = cum_value

        return commands
    
    # def calculate_double_declining_fiscal(self, commands, sequence, depreciation_date, amount, cum_value, res_value):
    #     depreciation_date = self.date
    #     get_first_day = date_utils.start_of(self.date, 'year')

    #     if self.first_depreciation_manual_date and self.first_depreciation_manual_date != self.date:
    #         # depreciation_date set manually from the 'first_depreciation_manual_date' field
    #         valid_date = int(self.first_depreciation_manual_date.strftime("%d"))
    #         if 1 <= valid_date <= 15:
    #             if self.is_reset_january:
    #                 depreciation_date = self.first_depreciation_manual_date
    #             else:
    #                 depreciation_date = get_first_day

    #         else:
    #             if self.is_reset_january:
    #                 next_month = date_utils.add(self.first_depreciation_manual_date, months=1)
    #                 date_min = date_utils.start_of(next_month, "month")
    #                 depreciation_date = date_min
    #             else:
    #                 depreciation_date = get_first_day

    def sub_double_dep_adding(self, obj, res_value, sequence, cum_value, depreciation_date, next_dep_count, p):
        commands = []
        amount_fiscal = (res_value * p )* next_dep_count / 12
        vals = {
            'amount_fiscal': amount_fiscal,
            'asset_id': obj.id,
            'sequence': sequence + 1,
            'name': (obj.code or '') + '/' + str(sequence),
            'depreciated_value_fiscal': round((cum_value + amount_fiscal),2),
            'remaining_value_fiscal': round((res_value - amount_fiscal),2),
            'depreciation_date_fiscal': depreciation_date + relativedelta(months=+12)
        }
        commands.append((0, 0, vals))
        return commands

    def _compute_board_undone_dotation_nb(self, depreciation_date, total_days):
        res = super(Asset, self)._compute_board_undone_dotation_nb(depreciation_date, total_days)
        undone_dotation_number = res
        if self.prorata and self.prorata_type == 'daily' and self.is_monthly_depreciation:
           undone_dotation_number = self.method_number 

        return undone_dotation_number

    def compute_depreciation_board(self):
        self.ensure_one()

        posted_depreciation_line_ids = self.depreciation_line_ids.filtered(lambda x: x.state == 'posted').sorted(
            key=lambda l: l.depreciation_date)
        unposted_depreciation_line_ids = self.depreciation_line_ids.filtered(lambda x: x.state in ['draft','unposted'])
        
        # Remove old unposted depreciation lines. We cannot use unlink() with One2many field
        commands = [(2, line_id.id, False) for line_id in unposted_depreciation_line_ids]

        if self.value_residual != 0.0:
            amount_to_depr = residual_amount = self.value_residual

            # if we already have some previous validated entries, starting date is last entry + method period
            if posted_depreciation_line_ids and posted_depreciation_line_ids[-1].depreciation_date:
                last_depreciation_date = fields.Date.from_string(posted_depreciation_line_ids[-1].depreciation_date)
                depreciation_date = last_depreciation_date + relativedelta(months=+self.method_period)
            else:
                get_first_day = date_utils.start_of(self.date, 'year')
                depreciation_date_manual = get_first_day + relativedelta(months=+self.method_period)

                depreciation_date = self.first_depreciation_manual_date
                if self.date_first_depreciation == 'last_day_period':
                    # depreciation_date = the last day of the month
                    depreciation_date = depreciation_date + relativedelta(day=31)
                    # ... or fiscalyear depending the number of period
                    if self.method_period == 12:
                        depreciation_date = depreciation_date + relativedelta(
                            month=self.company_id.fiscalyear_last_month)
                        depreciation_date = depreciation_date + relativedelta(
                            day=self.company_id.fiscalyear_last_day)
                        if depreciation_date < self.date:
                            depreciation_date = depreciation_date + relativedelta(years=1)
                elif self.first_depreciation_manual_date and self.first_depreciation_manual_date != self.date:
                    # depreciation_date set manually from the 'first_depreciation_manual_date' 
                    if self.is_reset_january == True:
                        depreciation_date = self.first_depreciation_manual_date
                    # else:
                    #     depreciation_date = get_first_day

            total_days = (depreciation_date.year % 4) and 365 or 366
            month_day = depreciation_date.day
            #current_amount = 0
            undone_dotation_number = self._compute_board_undone_dotation_nb(depreciation_date, total_days)
            salvage_value = self.salvage_value

            if self.method == 'linear' and not self.is_include_salvage_value:
                    residual_amount -= self.salvage_value

            if self.method == 'double_declining' and self.is_reset_january and not self.is_monthly_depreciation and depreciation_date.month != 1:
                undone_dotation_number += 1

            if self.prorata and self.prorata_type == 'daily' and self.is_monthly_depreciation:
                undone_dotation_number += 1
            elif self.is_reset_january:
                undone_dotation_number += 1
                
            _logger.exception(_("Debug: %s", range(len(posted_depreciation_line_ids), undone_dotation_number)))
            
            for x in range(len(posted_depreciation_line_ids), undone_dotation_number):
                sequence = x + 1
                amount = self._compute_board_amount(sequence, residual_amount, amount_to_depr, salvage_value,
                                                    undone_dotation_number, posted_depreciation_line_ids,
                                                    total_days, depreciation_date)
                            
                amount = self.currency_id.round(amount)
                if float_is_zero(amount, precision_rounding=self.currency_id.rounding):
                    continue

                residual_amount -= amount

                # if self.method_period == 12 and self.prorata and self.prorata_type == 'daily':
                #     depreciation_date = depreciation_date.replace(day=31, month=12)

                
                vals = {
                    'amount': amount,
                    'asset_id': self.id,
                    'sequence': sequence,
                    'name': (self.code or '') + '/' + str(sequence),
                    'remaining_value': residual_amount,
                    # 'depreciated_value': self.value - (self.salvage_value + residual_amount),
                    'depreciated_value': self.value - residual_amount,
                    'depreciation_date': depreciation_date,
                }
                

                if not self.is_include_salvage_value :
                    if self.method == 'linear' :
                        vals['depreciated_value'] = self.value - (self.salvage_value + residual_amount)
                    if self.method == 'double_declining' :
                        vals['remaining_value'] = residual_amount - self.salvage_value
                    if self.method == 'degressive' :
                        depreciated_value = self.value - residual_amount
                        vals['remaining_value'] = self.value - (depreciated_value + salvage_value)

                if vals['remaining_value'] < 0:
                    vals['remaining_value'] = 0

                commands.append((0, False, vals))

                depreciation_date = depreciation_date + relativedelta(months=+self.method_period)
                if self.prorata or self.is_reset_january:
                    depreciation_date = depreciation_date.replace(month=1)

                if month_day > 28 and self.date_first_depreciation == 'manual':
                    max_day_in_month = calendar.monthrange(depreciation_date.year, depreciation_date.month)[1]
                    depreciation_date = depreciation_date.replace(day=min(max_day_in_month, month_day))

                # datetime doesn't take into account that the number of days is not the same for each month
                if not self.prorata and self.method_period % 12 != 0 and self.date_first_depreciation == 'last_day_period':
                    max_day_in_month = calendar.monthrange(depreciation_date.year, depreciation_date.month)[1]
                    depreciation_date = depreciation_date.replace(day=max_day_in_month)
        
        depreciation_line_ids_fiscal = self.compute_fiscal_depreciation()
 
        if self.method == 'double_declining' and self.is_monthly_depreciation:
            command = self.calculate_double_declining(commands, posted_depreciation_line_ids)
            if self.is_reset_january:
                command = self.calculate_double_declining_reset_january(commands, posted_depreciation_line_ids)
            self.write({'depreciation_line_ids': command, 'depreciation_line_ids_fiscal' : depreciation_line_ids_fiscal})
        elif self.method == 'linear' and self.is_monthly_depreciation:
            command = self.calculate_linear(commands, posted_depreciation_line_ids)
            self.write({'depreciation_line_ids': command, 'depreciation_line_ids_fiscal' : depreciation_line_ids_fiscal, 'method_period': self.method_period})
        elif self.method == 'degressive' and self.is_monthly_depreciation:
            command = self.calculate_degressive(commands, posted_depreciation_line_ids)
            self.write({'depreciation_line_ids': command, 'depreciation_line_ids_fiscal' : depreciation_line_ids_fiscal})   
        else:
            self.write({'depreciation_line_ids': commands, 'depreciation_line_ids_fiscal' : depreciation_line_ids_fiscal})

        return True

    def validate(self):
        res = super(Asset, self).validate()
        for line in self.depreciation_line_ids:
            if not line.move_check:
                line.create_move()

        return res
    
    def calculate_degressive(self, commands, posted_depreciation_line_ids):
        depreciation_date = self.date
        # if we already have some previous validated entries, starting date is last entry + method period
        if posted_depreciation_line_ids and posted_depreciation_line_ids[-1].depreciation_date:
            last_depreciation_date = fields.Date.from_string(posted_depreciation_line_ids[-1].depreciation_date)
            depreciation_date = last_depreciation_date + relativedelta(months=+self.method_period)
        else:
            # depreciation_date computed from the purchase date
            depreciation_date = self.date
            if self.date_first_depreciation == 'last_day_period':
                # depreciation_date = the last day of the month
                depreciation_date = depreciation_date + relativedelta(day=31)
                # ... or fiscalyear depending the number of period
                if self.method_period == 12:
                    depreciation_date = depreciation_date + relativedelta(
                        month=self.company_id.fiscalyear_last_month)
                    depreciation_date = depreciation_date + relativedelta(
                        day=self.company_id.fiscalyear_last_day)
                    if depreciation_date < self.date:
                        depreciation_date = depreciation_date + relativedelta(years=1)
            elif self.first_depreciation_manual_date and self.first_depreciation_manual_date != self.date:
                # depreciation_date set manually from the 'first_depreciation_manual_date' field
                depreciation_date = self.first_depreciation_manual_date

        total_dep = self.method_number * self.method_period
        sequence_end = total_dep
        sequence_start = len(posted_depreciation_line_ids) + 1
        #if self.months_remaining:
        #    sequence_start += (self.method_number * self.method_period) - self.months_remaining

        start_last_year = sequence_end - 11
        sequence = 1
        command = []
        new_residual_amount = self.value_residual
        start_final_year_seq = (self.method_number * 12) - 11
        depreciated_value = 0
        for item in commands:
            if item[2]:
                amount_depreciation = item[2].get('amount') and float(item[2].get('amount')) / self.method_period or 0.0
                if self.prorata:
                    if commands[-1] == item:
                        remaining_month = self.first_depreciation_manual_date.month - item[2]['depreciation_date'].month
                    else:
                        remaining_month = 12 - item[2]['depreciation_date'].month + 1
                    amount_depreciation = item[2].get('amount') and float(item[2].get('amount')) / remaining_month or 0.0

                if self.is_reset_january:
                    if commands[-1] == item:
                        month_calc = self.first_depreciation_manual_date.month - item[2]['depreciation_date'].month
                        remaining_month = self.first_depreciation_manual_date.month - item[2]['depreciation_date'].month
                    else:
                        month_calc = 12
                        remaining_month = 12 - item[2]['depreciation_date'].month + 1
                    
                    if commands[-1] == item and self.is_convert_to_zero:
                        amount_depreciation = self.value - self.salvage_value - depreciated_value
                    else:
                        amount_depreciation = (self.method_progress_factor * (self.value - self.salvage_value - depreciated_value) * (month_calc / 12))
                    amount_depreciation = amount_depreciation / month_calc

                new_depreciation_value = 0.0
                remaining_amount = 0.0
                # if sequence == start_last_year:
                new_depreciation_value = amount_depreciation
                remaining_amount = new_residual_amount - (new_depreciation_value * 11)
                month_range = self.method_period
                if self.prorata or self.is_reset_january:
                   month_range = remaining_month
                for month in range(month_range):

                    if sequence < start_last_year:
                        depreciation_amount = amount_depreciation
                    elif sequence in range(start_last_year, start_last_year + 11):
                        depreciation_amount = new_depreciation_value
                    elif sequence == start_final_year_seq + 11:
                        # depreciation_amount = remaining_amount
                        depreciation_amount = new_depreciation_value
                    if sequence_start > sequence:
                        sequence += 1
                        depreciation_date += relativedelta(months=+1)
                        #if self.is_monthly_depreciation and self.months_remaining and total_dep > self.months_remaining:
                        #    new_residual_amount -= depreciation_amount
                        continue
                    new_residual_amount -= depreciation_amount
                    vals = {
                        'amount': depreciation_amount,
                        'asset_id': self.id,
                        'sequence': sequence,
                        'name': (self.code or '') + '/' + str(sequence),
                        'remaining_value': new_residual_amount,
                        # 'depreciated_value': self.value - (self.salvage_value + new_residual_amount),
                        'depreciated_value': self.value - new_residual_amount,
                        'depreciation_date': depreciation_date,
                    }
                    if not self.is_include_salvage_value:
                        vals['remaining_value'] = new_residual_amount - self.salvage_value
                    if self.is_include_salvage_value:
                        vals['remaining_value'] = new_residual_amount
                    if vals['remaining_value'] < 0:
                        vals['remaining_value'] = 0
                    command.append((0, False, vals))
                    depreciation_date += relativedelta(months=+1)
                    sequence += 1
                    depreciated_value = vals['depreciated_value']
            else:
                command.append(item)
        return command 

    def calculate_linear(self, commands, posted_depreciation_line_ids):
        depreciation_date = self.date
        # if we already have some previous validated entries, starting date is last entry + method period
        if posted_depreciation_line_ids and posted_depreciation_line_ids[-1].depreciation_date:
            last_depreciation_date = fields.Date.from_string(posted_depreciation_line_ids[-1].depreciation_date)
            depreciation_date = last_depreciation_date + relativedelta(months=+self.method_period)
        else:
            # depreciation_date computed from the purchase date
            depreciation_date = self.date
            if self.date_first_depreciation == 'last_day_period':
                # depreciation_date = the last day of the month
                depreciation_date = depreciation_date + relativedelta(day=31)
                # ... or fiscalyear depending the number of period
                if self.method_period == 12:
                    depreciation_date = depreciation_date + relativedelta(
                        month=self.company_id.fiscalyear_last_month)
                    depreciation_date = depreciation_date + relativedelta(
                        day=self.company_id.fiscalyear_last_day)
                    if depreciation_date < self.date:
                        depreciation_date = depreciation_date + relativedelta(years=1)
                else:
                    depreciation_date = self.first_depreciation_manual_date
            elif self.first_depreciation_manual_date and self.first_depreciation_manual_date != self.date:
                # depreciation_date set manually from the 'first_depreciation_manual_date' field
                depreciation_date = self.first_depreciation_manual_date
        
        
        total_dep = self.method_number * self.method_period
        sequence_end = total_dep
        sequence_start = len(posted_depreciation_line_ids) + 1
        #if self.months_remaining:
        #    sequence_start += (self.method_number * self.method_period) - self.months_remaining

        start_last_year = sequence_end - 11
        sequence = 1
        command = []
        new_residual_amount = self.value_residual
        #if self.is_monthly_depreciation and self.months_remaining and total_dep > self.months_remaining:
        #    new_residual_amount = self.value
        start_final_year_seq = (self.method_number * 12) - 11
        for item in commands:
            if item[2]:
                amount_depreciation = item[2].get('amount') and float(item[2].get('amount')) / self.method_period or 0.0
                if self.prorata:
                    if commands[-1] == item:
                        remaining_month = self.first_depreciation_manual_date.month - item[2]['depreciation_date'].month
                    else:
                        remaining_month = 12 - item[2]['depreciation_date'].month + 1
                    amount_depreciation = item[2].get('amount') and float(item[2].get('amount')) / remaining_month or 0.0
                new_depreciation_value = 0.0
                remaining_amount = 0.0
                # if sequence == start_last_year:
                new_depreciation_value = amount_depreciation
                remaining_amount = new_residual_amount - (new_depreciation_value * 11)
                month_range = self.method_period
                if self.prorata:
                   month_range = remaining_month
                for month in range(month_range):

                    if sequence < start_last_year:
                        depreciation_amount = amount_depreciation
                    elif sequence in range(start_last_year, start_last_year + 11):
                        depreciation_amount = new_depreciation_value
                    elif sequence == start_final_year_seq + 11:
                        # depreciation_amount = remaining_amount
                        depreciation_amount = new_depreciation_value
                        # if not self.is_include_salvage_value:
                        #     depreciation_amount = new_depreciation_value
                    if sequence_start > sequence:
                        sequence += 1
                        depreciation_date += relativedelta(months=+1)
                        #if self.is_monthly_depreciation and self.months_remaining and total_dep > self.months_remaining:
                        #    new_residual_amount -= depreciation_amount
                        continue
                    new_residual_amount -= depreciation_amount
                    vals = {
                        'amount': depreciation_amount,
                        'asset_id': self.id,
                        'sequence': sequence,
                        'name': (self.code or '') + '/' + str(sequence),
                        'remaining_value': new_residual_amount,
                        # 'depreciated_value': self.value - (self.salvage_value + new_residual_amount),
                        'depreciated_value': self.value - new_residual_amount,
                        'depreciation_date': depreciation_date,
                    }
                    if not self.is_include_salvage_value :
                        vals['remaining_value'] = new_residual_amount - self.salvage_value
                    if self.is_include_salvage_value :
                        vals['remaining_value'] = new_residual_amount
                    if vals['remaining_value'] < 0:
                        vals['remaining_value'] = 0
                    command.append((0, False, vals))
                    depreciation_date += relativedelta(months=+1)
                    
                    # if depreciation date is last date, show last date of the month
                    days_in_month = calendar.monthrange(self.first_depreciation_manual_date.year, self.first_depreciation_manual_date.month)[1]
                    is_last_day_of_month = self.first_depreciation_manual_date.day == days_in_month
                    if is_last_day_of_month:
                        days_in_month = calendar.monthrange(depreciation_date.year, depreciation_date.month)[1]
                        depreciation_date = datetime(depreciation_date.year, depreciation_date.month, days_in_month)

                    sequence += 1
            else:
                command.append(item)
        return command 
                
    def calculate_double_declining(self, commands, posted_depreciation_line_ids):
        depreciation_date = self.date
        get_first_day = date_utils.start_of(self.date, 'year')
        # if we already have some previous validated entries, starting date is last entry + method period
        if posted_depreciation_line_ids and posted_depreciation_line_ids[-1].depreciation_date:
            last_depreciation_date = fields.Date.from_string(posted_depreciation_line_ids[-1].depreciation_date)
            depreciation_date = last_depreciation_date + relativedelta(months=+self.method_period)
        else:
            # depreciation_date computed from the purchase date
            depreciation_date = self.date
            if self.date_first_depreciation == 'last_day_period':
                # depreciation_date = the last day of the month
                depreciation_date = depreciation_date + relativedelta(day=31)
                # ... or fiscalyear depending the number of period
                if self.method_period == 12:
                    depreciation_date = depreciation_date + relativedelta(
                        month=self.company_id.fiscalyear_last_month)
                    depreciation_date = depreciation_date + relativedelta(
                        day=self.company_id.fiscalyear_last_day)
                    if depreciation_date < self.date:
                        depreciation_date = depreciation_date + relativedelta(years=1)
            elif self.first_depreciation_manual_date and self.first_depreciation_manual_date != self.date:
                # depreciation_date set manually from the 'first_depreciation_manual_date' 
                    if self.is_reset_january == True:
                        depreciation_date = get_first_day  
                    else:
                        depreciation_date = self.first_depreciation_manual_date
        
        
        total_dep = self.method_number * self.method_period
        sequence_end = total_dep
        sequence_start = len(posted_depreciation_line_ids) + 1
        #if self.months_remaining:
        #    sequence_start += (self.method_number * self.method_period) - self.months_remaining

        start_last_year = sequence_end - 11
        sequence = 1
        command = []
        new_residual_amount = self.value_residual
        #if self.is_monthly_depreciation and self.months_remaining and total_dep > self.months_remaining:
        #    new_residual_amount = self.value
        start_final_year_seq = (self.method_number * 12) - 11
        for item in commands:
            if item[2]:
                amount_depreciation = item[2].get('amount') and float(item[2].get('amount')) / self.method_period or 0.0
                if self.prorata:
                    if commands[-1] == item:
                        remaining_month = self.first_depreciation_manual_date.month - item[2]['depreciation_date'].month
                    else:
                        remaining_month = 12 - item[2]['depreciation_date'].month + 1
                    amount_depreciation = item[2].get('amount') and float(item[2].get('amount')) / remaining_month or 0.0
                new_depreciation_value = 0.0
                remaining_amount = 0.0
                # if sequence == start_last_year:
                # new_depreciation_value = ((new_residual_amount / self.method_number) * 2) / 12
                new_depreciation_value = amount_depreciation
                remaining_amount = new_residual_amount - (new_depreciation_value * 11)
                month_range = self.method_period
                if self.prorata:
                   month_range = remaining_month
                for month in range(month_range):

                    if sequence < start_last_year:
                        depreciation_amount = amount_depreciation
                    elif sequence in range(start_last_year, start_last_year + 11):
                        depreciation_amount = new_depreciation_value
                    elif sequence == start_final_year_seq + 11:
                        depreciation_amount = new_depreciation_value
                    if sequence_start > sequence:
                        sequence += 1
                        depreciation_date += relativedelta(months=+1)
                        #if self.is_monthly_depreciation and self.months_remaining and total_dep > self.months_remaining:
                        #    new_residual_amount -= depreciation_amount
                        continue
                    new_residual_amount -= depreciation_amount
                    vals = {
                        'amount': depreciation_amount,
                        'asset_id': self.id,
                        'sequence': sequence,
                        'name': (self.code or '') + '/' + str(sequence),
                        'remaining_value': new_residual_amount,
                        'depreciated_value': self.value - new_residual_amount,
                        # 'depreciated_value': self.value - (self.salvage_value + new_residual_amount),
                        'depreciation_date': depreciation_date,
                    }
                    if not self.is_include_salvage_value :
                        vals['remaining_value'] = new_residual_amount - self.salvage_value
                    if self.is_include_salvage_value :
                        vals['remaining_value'] = new_residual_amount
                    if vals['remaining_value'] < 0:
                        vals['remaining_value'] = 0
                    command.append((0, False, vals))
                    depreciation_date += relativedelta(months=+1)
                    sequence += 1
            else:
                command.append(item)
        return command

    def _compute_months_remaining(self):
        depreciation_lines = self.env['account.asset.depreciation.line'].search([('asset_id', '=', self.id)], order='depreciation_date desc', limit=1)

        if len(depreciation_lines) > 0:
            depreciation_date = depreciation_lines.depreciation_date
            self.months_remaining = 12 - depreciation_date.month
        else:
            self.months_remaining = 0
            
    def calculate_double_declining_reset_january(self, commands, posted_depreciation_line_ids):
        depreciation_date = self.date
        # if we already have some previous validated entries, starting date is last entry + method period
        if posted_depreciation_line_ids and posted_depreciation_line_ids[-1].depreciation_date:
            last_depreciation_date = fields.Date.from_string(posted_depreciation_line_ids[-1].depreciation_date)
            depreciation_date = last_depreciation_date + relativedelta(months=+self.method_period)
        else:
            # depreciation_date computed from the purchase date
            depreciation_date = self.date
            if self.date_first_depreciation == 'last_day_period':
                # depreciation_date = the last day of the month
                depreciation_date = depreciation_date + relativedelta(day=31)
                # ... or fiscalyear depending the number of period
                if self.method_period == 12:
                    depreciation_date = depreciation_date + relativedelta(
                        month=self.company_id.fiscalyear_last_month)
                    depreciation_date = depreciation_date + relativedelta(
                        day=self.company_id.fiscalyear_last_day)
                    if depreciation_date < self.date:
                        depreciation_date = depreciation_date + relativedelta(years=1)
            elif self.first_depreciation_manual_date and self.first_depreciation_manual_date != self.date:
                # depreciation_date set manually from the 'first_depreciation_manual_date' field
                depreciation_date = self.first_depreciation_manual_date
        
        start_month = depreciation_date.month
        total_dep = self.method_number * self.method_period
        sequence_start = len(posted_depreciation_line_ids) + 1
        #if self.months_remaining:
        #    sequence_start += (self.method_number * self.method_period) - self.months_remaining
        #if self.is_depreciation_completed:
        #    sequence_start = total_dep + 1
        sequence = 1
        command = []
        total_years = self.method_number
        if start_month != 1:
            total_years += 1
        if not self.is_include_salvage_value:
            new_residual_amount = self.value - self.salvage_value
        else:
            new_residual_amount = self.value
        #cumulative_dep = 0.0
        depreciated_value = 0
        for item in range(total_years):
            # depreciation_amount = ((new_residual_amount / self.method_number) * 2) / 12
            if item == (total_years - 1): # last loop
                month_calc = self.first_depreciation_manual_date.month - depreciation_date.month
            else:
                month_calc = 12

            if item == (total_years - 1) and self.is_convert_to_zero:
                depreciation_amount = self.value - self.salvage_value - depreciated_value
            else:
                depreciation_amount = ((100 / self.method_number * 2) * (self.value - self.salvage_value - depreciated_value) / 100) * (month_calc / 12)
            depreciation_amount = depreciation_amount / month_calc

            for month in range(1, self.method_period+1):
                if start_month != 1 and item == 0 and start_month > month:
                    continue
                if sequence_start > sequence:
                    sequence += 1
                    depreciation_date += relativedelta(months=+1)
                    #if self.is_monthly_depreciation and self.months_remaining and total_dep > self.months_remaining:
                    #    new_residual_amount -= depreciation_amount
                    continue
                if sequence > (total_dep):
                    continue
                if sequence == total_dep:
                    depreciation_amount = depreciation_amount
                new_residual_amount -= depreciation_amount

                if not self.is_include_salvage_value:
                    depreciated_value = self.value - (self.salvage_value + new_residual_amount)
                else:
                    depreciated_value = self.value - new_residual_amount

                vals = {
                    'amount': depreciation_amount,
                    'asset_id': self.id,
                    'sequence': sequence,
                    'name': (self.code or '') + '/' + str(sequence),
                    'remaining_value': new_residual_amount,
                    'depreciated_value': depreciated_value,
                    'depreciation_date': depreciation_date,
                }

                if vals['remaining_value'] < 0:
                    vals['remaining_value'] = 0
                command.append((0, False, vals))
                depreciated_value = vals['depreciated_value']
                depreciation_date += relativedelta(months=+1)
                #cumulative_dep += depreciation_amount
                sequence += 1
        list_of_popup =[]
        for item in commands:
            if not item[2]:
                list_of_popup.append(item)
        command += list_of_popup
        return command

    def confirm_dispose_asset(self):
        category_id = self.category_id
        move_obj = self.env['account.move']
        asset_moves = self.env['account.move'].search([('account_asset_id', '=', self.id), ('move_type', '=', 'entry')])
        if asset_moves:
            raise ValidationError("You can not create another asset sale journal entry while you have done it before!")
        if self.asset_value_residual <= 0:
            raise ValidationError(_('To make a sale, the sale price must be filled in first'))
        company_id = self.company_id
        draft_depreciation_lines =  self.depreciation_line_ids.filtered(lambda r: r.move_id == False or r.move_id.state != 'posted')
        posted_depreciation_lines = self.depreciation_line_ids.filtered(lambda r: r.move_id == False or r.move_id.state == 'posted')
        if draft_depreciation_lines or posted_depreciation_lines:

            # Check if both accounts are of the same type
            dispose_account = category_id.dispose_account
            depreciation_account = category_id.account_depreciation_id
            if dispose_account.internal_group != depreciation_account.internal_group:
                dispose_account.internal_group = depreciation_account.internal_group
                # raise ValidationError(_('Both accounts must be of the same type (either both "Off-Balance Sheet" or both not).'))
            
            vals = {
                'name': '/',
                'date': self.date,
                'ref': self.name,
                'account_asset_id': self.id,
                'invoice_date': self.date,
                'amount_untaxed': self.asset_value_residual,
                'amount_total': self.asset_value_residual,
                'partner_id': self.partner_id.id or False,
                'journal_id': category_id.journal_id.id,
                'branch_id': self.branch_id.id,
                'analytic_group_ids': [(6, 0, self.analytic_tag_ids.ids)],
            }

            vals_debit_1 = {
                'account_id': category_id.dispose_account.id,
                'name': 'Disposal Entry',
                'debit': self.asset_value_residual,
                'credit': 0.0,
                'journal_id': category_id.journal_id.id,
                'date': self.date,
                'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
            }
            vals_credit_1 = {
                'account_id': category_id.account_asset_id.id,
                'name': 'Disposal Entry',
                'debit': 0.0,
                'credit': self.asset_value_residual,
                'journal_id': category_id.journal_id.id,
                'date': self.date,
                'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
            }

            move_id = move_obj.create(vals)
            move_line_1 = (0, 0, vals_debit_1)
            move_line_2 = (0, 0, vals_credit_1)
            move_id.write({'amount_untaxed': self.asset_value_residual, 'amount_total': self.asset_value_residual, 'line_ids': [move_line_1, move_line_2]})
            self.write({'state': 'dispose'})
            

    def _get_disposal_moves(self):
        move_ids = []
        for asset in self:
            # unposted_depreciation_line_ids = asset.depreciation_line_ids.filtered(lambda x: not x.move_check)
            unposted_depreciation_line_ids = asset.depreciation_line_ids.filtered(lambda r: r.move_id == False or r.move_id.state != 'posted')


            # unposted_depreciation_line_ids = asset.depreciation_line_ids.filtered(lambda x: x.move_check)
            if unposted_depreciation_line_ids:
                old_values = {
                    'method_end': asset.method_end,
                    'method_number': asset.method_number,
                }
                # Remove all unposted depr. lines
                # commands = [(2, line_id.id, False) for line_id in unposted_depreciation_line_ids]

                # Create a new depr. line with the residual amount and post it
                # sequence = len(asset.depreciation_line_ids) - len(unposted_depreciation_line_ids) + 1

                # today = fields.Datetime.today()
                # vals = {
                #     'amount': asset.value_residual,
                #     'asset_id': asset.id,
                #     'sequence': sequence,
                #     'name': (asset.code or '') + '/' + str(sequence),
                #     'remaining_value': 0,
                #     'depreciated_value': asset.value - asset.salvage_value,  # the asset is completely depreciated
                #     'depreciation_date': today,
                # }
                # commands.append((0, False, vals))

                # asset.write({'depreciation_line_ids': commands, 'method_end': today, 'method_number': sequence})

                move_check = False
                if asset.value - asset.value_residual == 0:
                    move_check = False
                else:
                    move_check = True

                tracked_fields = self.env['account.asset.asset'].fields_get(['method_number', 'method_end'])
                changes, tracking_value_ids = asset._message_track(tracked_fields, old_values)
                if changes:
                    asset.message_post(subject=_('Asset sold or disposed. Accounting entry awaiting for validation.'), tracking_value_ids=tracking_value_ids)
                move_ids += asset.depreciation_line_ids[-1].create_move(post_move=False, move_check=move_check)
        return move_ids

    def delete_depreciation(self):
        moves = self.env['account.move'].search([('account_asset_id', '=', self.id), ('move_type', '=', 'entry')],
                                                order='date desc', limit=1)
        if moves:
            for rec in self:
                for line in rec.depreciation_line_ids:
                    if not line.move_check:
                        if line.depreciation_date > moves.date:
                            line.unlink()


class AccountAssetDepreciationLine(models.Model):
    _inherit = 'account.asset.depreciation.line'

    state = fields.Selection([('draft','Draft'),('unposted','Unposted'),('posted','Posted')], string='Status', default='draft', compute='_compute_state', tracking=True)
    
    def post_lines_and_close_asset(self):
        # we re-evaluate the assets to determine whether we can close them
        for line in self:
            line.log_message_when_posted()
            asset = line.asset_id
            if asset.currency_id.is_zero(asset.asset_value_residual):
                asset.message_post(body=_("Document closed."))
                asset.write({'state': 'close'})

    @api.depends('move_posted_check', 'move_check')
    def _compute_state(self):
        for rec in self:
            if rec.move_posted_check:
                rec.state = 'posted'
            elif rec.move_check:
                rec.state = 'draft'
            else:
                rec.state = 'unposted'

    def create_move(self, post_move=True, move_check=False):
        created_moves = self.env['account.move']
        if self.asset_id.id:
            asset_moves = self.env['account.move'].search_count([('account_asset_id', '=', self.asset_id.id)])
            if asset_moves:
                raise ValidationError("Depreciation can not be created because the asset is already sold! 1")
        for line in self:
            # if line.move_id:
            if line.move_id and move_check == False:
                raise UserError(_('This depreciation is already linked to a journal entry. Please post or delete it.'))
            move_vals = self._prepare_move(line, move_check=move_check)
            move = self.env['account.move'].create(move_vals)
            move.write({'amount_untaxed': line.amount, 'amount_total': line.amount})
            line.write({'move_id': move.id, 'move_check': True})
            created_moves |= move
        if post_move and created_moves:
          created_moves.filtered(lambda m: any(m.asset_depreciation_ids.mapped('asset_id.category_id.open_asset'))).action_post()
        return [x.id for x in created_moves]

    def create_moveline(self, post_move=False, move_check=False):
        created_moves = self.env['account.move']
        if self.asset_id.id:
            asset_moves = self.env['account.move'].search_count([('account_asset_id', '=', self.asset_id.id)])
            if asset_moves:
                raise ValidationError("Depreciation can not be created because the asset is already sold! 2")
        for line in self:
            company_currency = line.asset_id.company_id.currency_id
            current_currency = line.asset_id.currency_id
            prec = company_currency.decimal_places
            depreciation_date = self.env.context.get('depreciation_date') or line.depreciation_date or fields.Date.context_today(self)
        
            amount = current_currency._convert(
                line.amount, company_currency, line.asset_id.company_id, depreciation_date)
            if line.move_id:
                raise UserError(_('This depreciation is already linked to a journal entry. Please post or delete it.'))
            move_vals = self._prepare_move(line, move_check=move_check)
            move = self.env['account.move'].create(move_vals)
            line.write({'move_id': move.id, 'move_check': True})
            if move.amount_untaxed == 0 and move.amount_total == 0:
                move.write({'amount_untaxed': amount, 'amount_total': amount})
            created_moves |= move
        if post_move and created_moves:
          created_moves.filtered(lambda m: any(m.asset_depreciation_ids.mapped('asset_id.category_id.open_asset'))).action_post()
        return [x.id for x in created_moves]


    def _prepare_move(self, line, move_check=False):
        category_id = line.asset_id.category_id
        account_analytic_id = line.asset_id.account_analytic_id
        analytic_tag_ids = line.asset_id.analytic_tag_ids
        depreciation_date = self.env.context.get('depreciation_date') or line.depreciation_date or fields.Date.context_today(self)
        company_currency = line.asset_id.company_id.currency_id
        current_currency = line.asset_id.currency_id
        prec = company_currency.decimal_places
        amount = current_currency._convert(
            line.amount, company_currency, line.asset_id.company_id, depreciation_date)
        asset_name = line.asset_id.name + ' (%s/%s)' % (line.sequence, len(line.asset_id.depreciation_line_ids))
        
        if move_check == False:
            # amount_value = current_currency._convert(line.asset_id.value, company_currency, line.asset_id.company_id, depreciation_date)
            move_line_1 = {
                'name': "Depreciation Entry",
                'account_id': category_id.account_depreciation_id.id,
                'debit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
                'credit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
                'partner_id': line.asset_id.partner_id.id,
                'analytic_account_id': account_analytic_id.id if category_id.type == 'sale' else False,
                'analytic_tag_ids': [(6, 0, line.asset_id.analytic_tag_ids.ids)],
                'currency_id': current_currency.id or False,
                'amount_currency': company_currency != current_currency and - 1.0 * line.amount or 0.0,
                }

            move_line_2 = {
                'name': "Depreciation Entry",
                'account_id': category_id.account_depreciation_expense_id.id,
                'credit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
                'debit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
                'partner_id': line.asset_id.partner_id.id,
                'analytic_account_id': account_analytic_id.id if category_id.type == 'purchase' else False,
                'analytic_tag_ids': [(6, 0, line.asset_id.analytic_tag_ids.ids)],
                'currency_id': current_currency.id or False,
                'amount_currency': company_currency != current_currency and line.amount or 0.0,
            }
            move_vals = {
                'ref': line.asset_id.code,
                'date': depreciation_date or False,
                'invoice_date': depreciation_date or False,
                'partner_id': line.asset_id.partner_id.id or False,
                'journal_id': category_id.journal_id.id,
                'branch_id': line.asset_id.branch_id.id,
                'analytic_group_ids': [(6, 0, line.asset_id.analytic_tag_ids.ids)],
                'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
            }
        elif move_check == True:
            amount_value = current_currency._convert(line.asset_id.value, company_currency, line.asset_id.company_id, depreciation_date)
            move_line_1 = {
                'name': asset_name,
                'account_id': category_id.account_asset_id.id,
                'debit': 0.0 if float_compare(amount_value, 0.0, precision_digits=prec) > 0 else -amount_value,
                'credit': amount_value if float_compare(amount_value, 0.0, precision_digits=prec) > 0 else 0.0,
                'partner_id': line.asset_id.partner_id.id,
                'analytic_account_id': account_analytic_id.id if category_id.type == 'sale' else False,
                'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if category_id.type == 'sale' else False,
                'currency_id': company_currency != current_currency and current_currency.id or False,
                'amount_currency': company_currency != current_currency and - 1.0 * line.amount or 0.0,
                }

            amount_depreciation_line = sum(line.asset_id.depreciation_line_ids.mapped('amount'))
            dep_amount = sum(line.asset_id.depreciation_line_ids.filtered(lambda r: r.move_id == False or r.move_id.state != 'posted').mapped('amount'))
            move_line_2 = {
                'name': asset_name,
                'account_id': category_id.dispose_account.id,
                'credit': 0.0 if float_compare(dep_amount, 0.0, precision_digits=prec) > 0 else -dep_amount,
                'debit': dep_amount if float_compare(dep_amount, 0.0, precision_digits=prec) > 0 else 0.0,
                'partner_id': line.asset_id.partner_id.id,
                'analytic_account_id': account_analytic_id.id if category_id.type == 'purchase' else False,
                'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if category_id.type == 'purchase' else False,
                'currency_id': company_currency != current_currency and current_currency.id or False,
                'amount_currency': company_currency != current_currency and line.amount or 0.0,
            }

            dispose_amount = amount_value - dep_amount
            move_line_3 = {
                'name': asset_name,
                'account_id': category_id.account_depreciation_id.id,
                'credit': 0.0 if float_compare(dispose_amount, 0.0, precision_digits=prec) > 0 else -dispose_amount,
                'debit': dispose_amount if float_compare(dispose_amount, 0.0, precision_digits=prec) > 0 else 0.0,
                'partner_id': line.asset_id.partner_id.id,
                'analytic_account_id': account_analytic_id.id if category_id.type == 'purchase' else False,
                'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if category_id.type == 'purchase' else False,
                'currency_id': company_currency != current_currency and current_currency.id or False,
                'amount_currency': company_currency != current_currency and line.amount or 0.0,
            }

            move_vals = {
                'ref': line.asset_id.code,
                'date': depreciation_date or False,
                'invoice_date': depreciation_date or False,
                'partner_id': line.asset_id.partner_id.id or False,
                'journal_id': category_id.journal_id.id,
                'branch_id': line.asset_id.branch_id.id,
                'analytic_group_ids': [(6, 0, analytic_tag_ids.ids)],
                'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2), (0, 0, move_line_3)],
            }
        # else:
        #     move_line_1 = {
        #         'name': asset_name,
        #         'account_id': category_id.account_depreciation_id.id,
        #         'debit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
        #         'credit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
        #         'partner_id': line.asset_id.partner_id.id,
        #         'analytic_account_id': account_analytic_id.id if category_id.type == 'sale' else False,
        #         'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if category_id.type == 'sale' else False,
        #         'currency_id': company_currency != current_currency and current_currency.id or False,
        #         'amount_currency': company_currency != current_currency and - 1.0 * line.amount or 0.0,
        #     }

        #     move_line_2 = {
        #         'name': asset_name,
        #         'account_id': category_id.account_depreciation_expense_id.id,
        #         'credit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
        #         'debit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
        #         'partner_id': line.asset_id.partner_id.id,
        #         'analytic_account_id': account_analytic_id.id if category_id.type == 'purchase' else False,
        #         'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if category_id.type == 'purchase' else False,
        #         'currency_id': company_currency != current_currency and current_currency.id or False,
        #         'amount_currency': company_currency != current_currency and line.amount or 0.0,
        #     }
        #     move_vals = {
        #         'ref': line.asset_id.code,
        #         'date': depreciation_date or False,
        #         'journal_id': category_id.journal_id.id,
        #         'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
        #     }
        return move_vals

    def unlink(self):
        for record in self:
            if record.state == 'posted':
                if record.asset_id.category_id.type == 'purchase':
                    msg = _("You cannot delete posted depreciation lines.")
                else:
                    msg = _("You cannot delete posted installment lines.")
                raise UserError(msg)
        return models.Model.unlink(self)
    
    
class AccountAssetFiscalLine(models.Model):
    _name = 'account.asset.fiscal.line'
    _description = 'Fiscal depreciation line'
    _order = "sequence"

    name = fields.Char(string='Depreciation Name', required=True, index=True)
    sequence = fields.Integer(required=True)
    asset_id = fields.Many2one('account.asset.asset', string='Asset', required=True, ondelete='cascade')
    amount_fiscal = fields.Float(string='Current Depreciation', digits=0, required=True)
    remaining_value_fiscal = fields.Float(string='Next Period Depreciation', digits=0, required=True)
    depreciated_value_fiscal = fields.Float(string='Cumulative Depreciation', required=True)
    depreciation_date_fiscal = fields.Date('Depreciation Date', index=True)

    
class AccountAssetCategoryFiscal(models.Model):
    _name = 'account.asset.category.fiscal'
    _description = 'Fiscal Asset Group'
    _rec_name = 'asset_category_id'


    asset_category_id = fields.Many2one('account.asset.category', string='Fiscal Asset Type', required=True, domain=[('is_fiscal_asset_type', '!=', True)])
    is_fiscal_asset_type = fields.Boolean(compute='_compute_is_fiscal_asset_type', store=False)
    method_time = fields.Selection([('number', 'Number of Entries'), ('end', 'Ending Date')], string='Time Method', default='number',
        help="Choose the method to use to compute the dates and number of entries.\n"
           "  * Number of Entries: Fix the number of entries and the time between 2 depreciations.\n"
           "  * Ending Date: Choose the time between 2 depreciations and the date the depreciations won't go beyond.")
    method_number = fields.Integer(string='Number of Depreciations', default=5)
    method_period = fields.Integer(string='One Entry Every', default=12, help="The amount of time between two depreciations, in months")
    method_end = fields.Date('Ending date')    
    method = fields.Selection([('linear', 'Straight-line Method'), ('double_declining', 'Declining Balance Method')], string='Computation Method', default='linear')
    asset_type = fields.Selection([('building', 'Building'), ('non_building', 'Non-Building')], string='Asset type',
                                  default='building')
    asset_type_1 = fields.Selection([('non_building', 'Non-Building')], string='Asset type')
    sub_asset_type = fields.Selection([('permanent', 'Permanent'), ('non_permanent', 'Non-Permanent')],
                                      default='permanent')
    non_building_type = fields.Selection(
        [('one_four', 'Category 1'), ('two_eight', 'Category 2'), ('three_sixteen', 'Category 3'),
         ('four_twenty', 'Category 4')])
    method_number_fiscal = fields.Integer(string='Number of Depreciations', readonly=True,
                                          help="The number of depreciations needed to depreciate your asset")
    prorata = fields.Boolean(string='Prorata Temporis', help='Indicates that the first depreciation entry for this asset have to be done from the purchase date instead of the first of January')
    cut_off_asset_date = fields.Integer(string='Cut Off Asset Date', default=31)
    is_monthly_depreciation = fields.Boolean(string='Monthly Depreciation')
    is_reset_january = fields.Boolean(string='Reset on January')
    double_declining_method_number = fields.Integer(string='Number of Depreciations', default=5, help="The number of depreciations needed to depreciate your asset")
    double_declining_method_period = fields.Integer(string='Number of Months in a Period', default=12,
        help="The amount of time between two depreciations, in months")

    @api.onchange('method')
    def onchange_method(self):
        for rec in self:
            if rec.method == 'double_declining':
                rec.asset_type = 'non_building'
                rec.asset_type_1 = 'non_building'

    @api.onchange('asset_type', 'sub_asset_type', 'non_building_type', 'permanent_type', 'non_permanent_type')
    def onchange_depreciation(self):
        for rec in self:
            if rec.asset_type == 'building':
                if rec.sub_asset_type == 'permanent':
                    rec.method_number = 20
                if rec.sub_asset_type == 'non_permanent':
                    rec.method_number = 10
            if rec.asset_type == 'non_building':
                if rec.non_building_type == 'one_four':
                    rec.method_number = 4
                if rec.non_building_type == 'two_eight':
                    rec.method_number = 8
                if rec.non_building_type == 'three_sixteen':
                    rec.method_number = 16
                if rec.non_building_type == 'four_twenty':
                    rec.method_number = 20

    def _compute_is_fiscal_asset_type(self):
        for rec in self:
            if rec.asset_category_id:
                rec.asset_category_id.update({"is_fiscal_asset_type": True})
                rec.is_fiscal_asset_type = True

    def manage_type(self):
        # query_statement = """SELECT asset_category_id FROM account_asset_category_fiscal LEFT JOIN account_asset_category ON account_asset_category_fiscal.asset_category_id=account_asset_category.id"""
        query_statement = """SELECT asset_category_id FROM account_asset_category_fiscal"""
        self.env.cr.execute(query_statement)
        type_id = self.env.cr.dictfetchall()
        type_list = [type_id['asset_category_id'] for type_id in type_id]
        for t in type_list:
            query_statement_2 = """UPDATE account_asset_category set is_fiscal_asset_type = False"""
            query_statement_3 ="""UPDATE account_asset_category set is_fiscal_asset_type = True WHERE id = %s """
            self.sudo().env.cr.execute(query_statement_2)
            self.sudo().env.cr.execute(query_statement_3, [t])

    def write(self, values):
        res = super(AccountAssetCategoryFiscal, self).write(values)
        self.manage_type()
        return res

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        raise UserError(_('You cannot duplicate a Fiscal Asset Group.'))

    def unlink(self):
        for categ in self:
            categ.asset_category_id.update({"is_fiscal_asset_type": False})
        return super(AccountAssetCategoryFiscal, self).unlink()

class AssetAssetRevalueWizard(models.TransientModel):
    _name = 'asset.asset.revalue.wizard'
    _description = 'Asset Revaluation Wizard'
    
    def default_get(self, default_fields):
        context = self._context
        active_id = context.get('active_id', False)
        company = self.env['res.company'].browse([self.env.company])
        result = super(AssetAssetRevalueWizard, self).default_get(default_fields)
        if active_id:
            asset = self.env['account.asset.asset'].browse([active_id])
            result['original_value'] = asset.value
            result['remaining_value'] = asset.value_residual + asset.salvage_value
            result['currency_id'] = asset.currency_id.id or company.currency_id.id
        return result
    
    def _get_default_method_number(self):
        return self.env['account.asset.asset'].browse(self._context.get('active_id')).method_number
    
    def _get_default_method_period(self):
        return self.env['account.asset.asset'].browse(self._context.get('active_id')).method_period
    
    reason = fields.Char('Reason', required=True)
    original_value = fields.Monetary('Original Amount', readonly=True, currency_field='currency_id', required=True)
    remaining_value = fields.Monetary('Current Amount', readonly=True, currency_field='currency_id', required=True)
    amount = fields.Monetary('Revalued Amount', currency_field='currency_id', required=True)
    journal_id = fields.Many2one('account.journal', 'Revalued Entry', required=True)
    method_number = fields.Integer('Number of Depreciation', default=_get_default_method_number)
    method_period = fields.Integer('Interval', default=_get_default_method_period)
    company_id = fields.Many2one('res.company', store=True, readonly=True, default=lambda self: self.env.company)
    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency',
        readonly=True, store=True,
        help='Utility field to express amount currency')
    currency_id = fields.Many2one('res.currency', string='Currency',
        readonly=True, store=True,
        help='Utility field to express amount currency')
    

    salvage_value = fields.Float(string="Salvage Value")
    asset_depreciation_manual_date = fields.Date(string="First Depreciation Date")

    def confirm_revalue_asset(self):

        asset_revalue_obj = self.env['asset.asset.revalue']
        move_obj = self.env['account.move']
        context = self._context
        company_id = self.company_id
        move = False
        active_id = context.get('active_id', False)
        if active_id:
            asset = self.env['account.asset.asset'].browse([active_id])
            
            unposted_depreciation_line_ids = asset.depreciation_line_ids.filtered(lambda x: not x.move_check).sorted(
            key=lambda l: l.depreciation_date)

            # if unposted_depreciation_line_ids:
            #     # Remove all unposted depr. lines
            #     commands = [(2, line_id.id, False) for line_id in unposted_depreciation_line_ids]
            #
            #     # Create a new depr. line with the residual amount and post it
            #     sequence = len(asset.depreciation_line_ids) - len(unposted_depreciation_line_ids) + 1
            #     today = fields.Datetime.today()

            if len(unposted_depreciation_line_ids) == len(asset.depreciation_line_ids):
                if self.remaining_value == self.amount:
                    raise ValidationError("The revaluation amount is the same as the remaining amount while there is no depreciation. Please check the amount or the depreciation to revalue this asset!")
            
                if self.remaining_value > self.amount:

                    move_line_1 = {
                    'name': 'account',
                    'account_id': asset.category_id.account_revaluation_loss_id.id,
                    'debit': self.remaining_value - self.amount,
                    'credit': 0.0,
                    # 'journal_id': category_id.journal_id.id,
                    # 'partner_id': partner.id,
                    # 'analytic_account_id': category_id.account_analytic_id.id if category_id.type == 'sale' else False,
                    'currency_id': asset.currency_id.id
                    # 'amount_currency': company_currency != current_currency and - 1.0 * line.amount or 0.0,
                    }
                    move_line_2 = {
                    'name': 'account',
                    'account_id': asset.category_id.account_asset_id.id,
                    'debit': 0.0,
                    'credit': self.remaining_value - self.amount,
                    # 'journal_id': category_id.journal_id.id,
                    # 'partner_id': partner.id,
                    # 'analytic_account_id': category_id.account_analytic_id.id if category_id.type == 'sale' else False,
                    'currency_id': asset.currency_id.id
                    # 'amount_currency': company_currency != current_currency and - 1.0 * line.amount or 0.0,
                    }
                    move_vals = {
                        'ref': asset.name,
                        # 'date': depreciation_date or False,
                        'journal_id': asset.category_id.journal_id.id,
                        'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
                    }
                    
                    move = self.env['account.move'].create(move_vals)
                    move.action_post()

                if self.remaining_value < self.amount:

                    move_line_1 = {
                    'name': 'account',
                    'account_id': asset.category_id.account_asset_id.id,
                    'debit':  self.amount - self.remaining_value,
                    'credit': 0.0,
                    # 'journal_id': category_id.journal_id.id,
                    # 'partner_id': partner.id,
                    # 'analytic_account_id': category_id.account_analytic_id.id if category_id.type == 'sale' else False,
                    'currency_id': asset.currency_id.id
                    # 'amount_currency': company_currency != current_currency and - 1.0 * line.amount or 0.0,
                    }
                    move_line_2 = {
                    'name': 'account',
                    'account_id': asset.category_id.account_revaluation_surplus_id.id,
                    'debit': 0.0,
                    'credit': self.amount - self.remaining_value,
                    # 'journal_id': category_id.journal_id.id,
                    # 'partner_id': partner.id,
                    # 'analytic_account_id': category_id.account_analytic_id.id if category_id.type == 'sale' else False,
                    'currency_id': asset.currency_id.id
                    # 'amount_currency': company_currency != current_currency and - 1.0 * line.amount or 0.0,
                    }
                    move_vals = {
                        'ref': asset.name,
                        # 'date': depreciation_date or False,
                        'journal_id': asset.category_id.journal_id.id,
                        'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
                    }
                    
                    move = self.env['account.move'].create(move_vals)
                    move.action_post()


            posted_depreciation_line_ids = asset.depreciation_line_ids.filtered(lambda x: x.move_check).sorted(
            key=lambda l: l.depreciation_date)
            
            sum_am = 0
            for line in posted_depreciation_line_ids:
                sum_am += line.amount

            
            if posted_depreciation_line_ids:
                if self.remaining_value == self.amount:
                    move_line_1 = {
                    'name': 'account',
                    'account_id': asset.category_id.account_depreciation_id.id,
                    'debit': sum_am,
                    'credit': 0.0,
                    # 'journal_id': category_id.journal_id.id,
                    # 'partner_id': partner.id,
                    # 'analytic_account_id': category_id.account_analytic_id.id if category_id.type == 'sale' else False,
                    'currency_id': asset.currency_id.id
                    # 'amount_currency': company_currency != current_currency and - 1.0 * line.amount or 0.0,
                    }
                    move_line_2 = {
                    'name': 'account',
                    'account_id': asset.category_id.account_asset_id.id,
                    'debit': 0.0,
                    'credit': sum_am,
                    # 'journal_id': category_id.journal_id.id,
                    # 'partner_id': partner.id,
                    # 'analytic_account_id': category_id.account_analytic_id.id if category_id.type == 'sale' else False,
                    'currency_id': asset.currency_id.id
                    # 'amount_currency': company_currency != current_currency and - 1.0 * line.amount or 0.0,
                    }
                    move_vals = {
                        'ref': asset.name,
                        # 'date': depreciation_date or False,
                        'journal_id': asset.category_id.journal_id.id,
                        'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
                    }
                    
                    move = self.env['account.move'].create(move_vals)
                    move.action_post()
            
                elif self.remaining_value > self.amount:

                    move_line_3 = {
                    'name': 'account',
                    'account_id': asset.category_id.account_depreciation_id.id,
                    'debit': sum_am,
                    'credit': 0.0,
                    # 'journal_id': category_id.journal_id.id,
                    # 'partner_id': partner.id,
                    # 'analytic_account_id': category_id.account_analytic_id.id if category_id.type == 'sale' else False,
                    'currency_id': asset.currency_id.id
                    # 'amount_currency': company_currency != current_currency and - 1.0 * line.amount or 0.0,
                    }

                    move_line_1 = {
                    'name': 'account',
                    'account_id': asset.category_id.account_revaluation_loss_id.id,
                    'debit': self.remaining_value - self.amount,
                    'credit': 0.0,
                    # 'journal_id': category_id.journal_id.id,
                    # 'partner_id': partner.id,
                    # 'analytic_account_id': category_id.account_analytic_id.id if category_id.type == 'sale' else False,
                    'currency_id': asset.currency_id.id
                    # 'amount_currency': company_currency != current_currency and - 1.0 * line.amount or 0.0,
                    }
                    move_line_2= {
                    'name': 'account',
                    'account_id': asset.category_id.account_asset_id.id,
                    'debit': 0.0,
                    'credit': sum_am + (self.remaining_value - self.amount),
                    # 'journal_id': category_id.journal_id.id,
                    # 'partner_id': partner.id,
                    # 'analytic_account_id': category_id.account_analytic_id.id if category_id.type == 'sale' else False,
                    'currency_id': asset.currency_id.id
                    # 'amount_currency': company_currency != current_currency and - 1.0 * line.amount or 0.0,
                    }
                    move_vals = {
                        'ref': asset.name,
                        # 'date': depreciation_date or False,
                        'journal_id': asset.category_id.journal_id.id,
                        'line_ids': [(0, 0, move_line_3), (0, 0, move_line_1), (0, 0, move_line_2)],
                    }
                    
                    move = self.env['account.move'].create(move_vals)
                    move.action_post()

                elif self.remaining_value < self.amount:
                    move_line_3 = {
                    'name': 'account',
                    'account_id': asset.category_id.account_asset_id.id,
                    'debit': -(sum_am - (self.amount - self.remaining_value)) if sum_am - (self.amount - self.remaining_value) < 0 else sum_am - (self.amount - self.remaining_value),
                    'credit': 0.0,
                    # 'journal_id': category_id.journal_id.id,
                    # 'partner_id': partner.id,
                    # 'analytic_account_id': category_id.account_analytic_id.id if category_id.type == 'sale' else False,
                    'currency_id': asset.currency_id.id
                    # 'amount_currency': company_currency != current_currency and - 1.0 * line.amount or 0.0,
                    }

                    move_line_1 = {
                    'name': 'account',
                    'account_id': asset.category_id.account_revaluation_surplus_id.id,
                    'debit':  0.0,
                    'credit': self.amount - self.remaining_value,
                    # 'journal_id': category_id.journal_id.id,
                    # 'partner_id': partner.id,
                    # 'analytic_account_id': category_id.account_analytic_id.id if category_id.type == 'sale' else False,
                    'currency_id': asset.currency_id.id
                    # 'amount_currency': company_currency != current_currency and - 1.0 * line.amount or 0.0,
                    }
                    move_line_2 = {
                    'name': 'account',
                    'account_id': asset.category_id.account_depreciation_id.id,
                    'debit': sum_am,
                    'credit': 0.0  ,
                    # 'journal_id': category_id.journal_id.id,
                    # 'partner_id': partner.id,
                    # 'analytic_account_id': category_id.account_analytic_id.id if category_id.type == 'sale' else False,
                    'currency_id': asset.currency_id.id
                    # 'amount_currency': company_currency != current_currency and - 1.0 * line.amount or 0.0,
                    }
                    move_vals = {
                        'ref': asset.name,
                        # 'date': depreciation_date or False,
                        'journal_id': asset.category_id.journal_id.id,
                        # 'line_ids': [(0, 0, move_line_3), (0, 0, move_line_1), (0, 0, move_line_2)],
                        'line_ids': [(0, 0, move_line_2), (0, 0, move_line_3), (0, 0, move_line_1)],
                    }
                    move = self.env['account.move'].create(move_vals)
                    move.action_post()
            # for line in posted_depreciation_line_ids:
                # if line.move_id:
                    # line.move_id.button_cancel()
                    # line.write({'move_check' : False, 'move_id' : False})
                    
            # asset_vals= {
            #     'value' : self.amount,
            #     'method_number' : self.method_number,
            #     'method_period' : self.method_period,
            #     'salvage_value' : self.salvage_value,
            #     'first_depreciation_manual_date' : self.asset_depreciation_manual_date,
            # }
            # asset.write(asset_vals)
            if unposted_depreciation_line_ids:
                # Remove all unposted depr. lines
                commands = [(2, line_id.id, False) for line_id in unposted_depreciation_line_ids]

                # Create a new depr. line with the residual amount and post it
                sequence = len(asset.depreciation_line_ids) - len(unposted_depreciation_line_ids) + 1
                today = fields.Datetime.today()
                asset_vals = {
                    'amount': asset.value_residual,
                    'asset_id': asset.id,
                    'sequence': sequence,
                    'name': (asset.code or '') + '/' + str(sequence),
                    'remaining_value': 0,
                    'depreciated_value': asset.value - asset.salvage_value,  # the asset is completely depreciated
                    'depreciation_date': today,
                }
                commands.append((0, False, asset_vals))
                asset.write({'depreciation_line_ids': commands, 'method_end': today, 'method_number': sequence})
            

            # asset.compute_depreciation_board()
            asset.write({'state': 'close'})
            vals = {
                'reason' : self.reason,
                'asset_id' : active_id,
                'remaining_value' : self.remaining_value,
                'amount' : self.amount,
                'journal_id' : self.journal_id.id,
                'method_number' : self.method_number,
                'method_period' : self.method_period,
                'user_id' : self.env.uid,
                'date' : fields.Date.today(),
                'prev_method_number' : asset.method_number,
                'prev_method_period' : asset.method_period,
            }
            asset_revalue_obj.create(vals)         
        

        vals_new_asset = {'name' : asset.name,
                         'category_id' : asset.category_id.id,
                         'fiscal_category_id' : asset.fiscal_category_id.id,
                         'code' : asset.code,
                         'date' : asset.date,
                         'value' : self.amount,
                         'method_number' : self.method_number,
                         'method_period' : self.method_period,
                         'salvage_value' : self.salvage_value,
                         'first_depreciation_manual_date' : self.asset_depreciation_manual_date,
                         'is_revaluation_asset' : True,
                         }
        new_asset = self.env['account.asset.asset'].create(vals_new_asset)
        revalued_asset = self.env['asset.asset.revalue'].search([('asset_id', '=', active_id)], order='id desc', limit=1)
        revalued_asset.revalue_asset_id = new_asset.id
        print("revalued_asset",revalued_asset)
        return {
                'name': 'Assets',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.asset.asset',
                'res_id': new_asset.id,
            }
    
    
            
    
class AssetAssetRevalue(models.Model):
    _name = 'asset.asset.revalue'
    _description = 'Asset Revaluation'
    _rec_name = 'reason'


    
    reason = fields.Char('History')
    asset_id = fields.Many2one('account.asset.asset', 'Asset', Required=True)
    revalue_asset_id = fields.Many2one('account.asset.asset', 'Revalued Asset')
    remaining_value = fields.Monetary('Previous Amount', readonly=True, currency_field='currency_id')
    amount = fields.Monetary('New Amount', currency_field='currency_id')
    journal_id = fields.Many2one('account.journal', 'Revalued Entry')
    method_number = fields.Integer('Number of Depreciation')
    method_period = fields.Integer('Number of Months')
    user_id = fields.Many2one('res.users', 'User')
    date = fields.Date('Date')
    prev_method_number = fields.Integer('Previous Number of Depreciation')
    prev_method_period = fields.Integer('Previous Number of Months')
    dispose_price = fields.Float('Dispose Price')
    company_id = fields.Many2one('res.company', store=True, readonly=True, default=lambda self: self.env.company)
    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency',
        readonly=True, store=True,
        help='Utility field to express amount currency')
    currency_id = fields.Many2one(related='asset_id.currency_id', string='Currency',
        readonly=True, store=True,
        help='Utility field to express amount currency')

class AssetCip(models.Model):
    _name = 'asset.cip'
    _description = 'Asset CIP'


    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one(
        'res.branch',
        check_company=True,
        tracking=True,
        domain=_domain_branch,
        default = _default_branch,
        readonly=False)
    
    name = fields.Char(required = True,default="New")
    asset_name = fields.Char('Asset Name',required = True)
    asset_category = fields.Many2one('account.asset.category', 'Asset Category')
    cip_account = fields.Many2one('account.account')
    state = fields.Selection([
            ('draft', 'Draft'),
            ('in_progress', 'In Progress'),
            ('posted', 'Posted')
        ], string='Status')

    lines = fields.One2many('asset.cip.line','cip_id')
    currency = fields.Many2one('res.currency')
    entry_count = fields.Integer(compute='compute_journal_count')
    move_id = fields.Many2one('account.move')
    asset_count = fields.Integer(compute='compute_asset_count')
    amount_total = fields.Float(compute='compute_amount_total')
    

    def action_post(self):
     
        amount = 0
        for line in self.lines:
            amount += line.amount
            if not line.move_check:
                raise UserError(_(
                'The progress of Construction in Progress is not yet done. Please post the related journal entries.'))
   
        self.state = 'posted'
        category_id = self.asset_category
        move_line_1 = {
            'name': self.asset_name,
            'account_id': self.cip_account.id,
            'debit': 0.0,
            'credit': amount,
            'journal_id': category_id.journal_id.id,
            # 'partner_id': partner.id,
            # 'analytic_account_id': category_id.account_analytic_id.id if category_id.type == 'sale' else False,
            'currency_id': self.currency.id
            # 'amount_currency': company_currency != current_currency and - 1.0 * line.amount or 0.0,
        }
        move_line_2 = {
            'name': self.asset_name,
            'account_id': self.asset_category.account_asset_id.id,
            'credit': 0.0,
            'debit': amount,
            'journal_id': category_id.journal_id.id,
            # 'partner_id': partner.id,
            # 'analytic_account_id': category_id.account_analytic_id.id if category_id.type == 'purchase' else False,
            'currency_id': self.currency.id
            # 'amount_currency': company_currency != current_currency and line.amount or 0.0,
        }
        move_vals = {
            'ref': self.name,
            # 'date': depreciation_date or False,
            'journal_id': category_id.journal_id.id,
            'branch_id': self.branch_id.id,
            'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
        }
        move = self.env['account.move'].create(move_vals)
        self.move_id = move.id

        return {
            'name':_("Create Asset"),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.asset.create',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def compute_journal_count(self):
        for asset in self:
            asset.entry_count = 0
            for line in asset.lines:

                if line.move_id:
                    asset.entry_count += 1
            if asset.move_id:
                asset.entry_count += 1

    def compute_asset_count(self):
        for cip in self:
            assets = self.env['account.asset.asset'].search([('account_cip_id', '=', cip.id)])
            cip.asset_count = len(assets.ids) or 0


    
    @api.depends('lines','lines.amount')
    def compute_amount_total(self):
        for rec in self:
            total = 0
            for line in rec.lines:
                total += line.amount
            rec.amount_total = total
    
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('asset.cip') or 'New'
        result = super(AssetCip, self).create(vals)
        return result

    def open_entries(self):
        move_ids = []
        for asset in self:
            for line in asset.lines:
                if line.move_id:
                    move_ids.append(line.move_id.id)

        if self.move_id:             
            move_ids.append(self.move_id.id)  
                  
        return {
            'name': _('Journal Entries'),
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', move_ids)],
        }    


    def open_assets(self):
        for cip in self:
            assets = self.env['account.asset.asset'].search([('account_cip_id', '=', cip.id)])
                  
            return {
                'name': _('Asset'),
                'view_mode': 'tree,form',
                'res_model': 'account.asset.asset',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', assets.ids)],
            }  

class AssetCipLine(models.Model):
    _name = 'asset.cip.line'

    product_id = fields.Many2one('product.template')
    label = fields.Char(required=True)
    account_id = fields.Many2one('account.account')
    # action = fields.Boolean()
    amount = fields.Float(string='Amount')
    cip_id = fields.Many2one('asset.cip')
    move_id = fields.Many2one('account.move')
    move_check = fields.Boolean(string="Action",_compute='_get_move_check')  
    move_posted_check = fields.Boolean(compute='_get_move_posted_check', string='Posted', store=True)
   
    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.move_posted_check:
            raise UserError(_(
                'The journal entry linked is now posted and can not be edited. Please make another line to make a change.'))
    
    @api.onchange('label')
    def onchange_label(self):
        if self.move_posted_check:
            raise UserError(_(
                'The journal entry linked is now posted and can not be edited. Please make another line to make a change.'))
        
    @api.onchange('account_id')
    def onchange_account_id(self):
        if self.move_posted_check:
            raise UserError(_(
                'The journal entry linked is now posted and can not be edited. Please make another line to make a change.'))
                
    @api.onchange('amount')
    def onchange_amount(self):
        if self.move_posted_check:
            raise UserError(_(
                'The journal entry linked is now posted and can not be edited. Please make another line to make a change.'))             

    @api.depends('move_id.state')
    def _get_move_posted_check(self):
        for line in self:
            line.move_posted_check = True if line.move_id and line.move_id.state == 'posted' else False

    @api.depends('move_id')
    def _get_move_check(self):
        for line in self:
            line.move_check = bool(line.move_id)

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.label = self.product_id.name
            self.account_id = self.product_id.property_account_expense_id.id

    def create_moveline(self, post_move=True):
        created_moves = self.env['account.move']
        prec = self.env['decimal.precision'].precision_get('Account')
        if self.mapped('move_id'):
            raise UserError(_(
                'A record of journal entry has linked to this line. Please check the journal entry to process the next step.'))
        for line in self:
            category_id = line.cip_id.asset_category
            # depreciation_date = self.env.context.get(
            #     'depreciation_date') or line.depreciation_date or fields.Date.context_today(
            #     self)
            # company_currency = line.asset_id.company_id.currency_id
            # current_currency = line.asset_id.currency_id
            # amount = current_currency.with_context(
            #     date=depreciation_date).compute(line.amount, company_currency)
            # asset_name = line.asset_id.name + ' (%s/%s)' % (
            # line.sequence, len(line.asset_id.depreciation_line_ids))
            # partner = self.env['res.partner']._find_accounting_partner(
            #     line.asset_id.partner_id)
            move_line_1 = {
                'name': line.label,
                'account_id': line.account_id.id,
                'debit': 0.0,
                'credit': line.amount,
                'journal_id': category_id.journal_id.id,
                # 'partner_id': partner.id,
                # 'analytic_account_id': category_id.account_analytic_id.id if category_id.type == 'sale' else False,
                'currency_id': line.cip_id.currency.id
                # 'amount_currency': company_currency != current_currency and - 1.0 * line.amount or 0.0,
            }
            move_line_2 = {
                'name': line.label,
                'account_id': line.cip_id.cip_account.id,
                'credit': 0.0,
                'debit': line.amount,
                'journal_id': category_id.journal_id.id,
                # 'partner_id': partner.id,
                # 'analytic_account_id': category_id.account_analytic_id.id if category_id.type == 'purchase' else False,
                'currency_id': line.cip_id.currency.id,
                # 'amount_currency': company_currency != current_currency and line.amount or 0.0,
            }
            move_vals = {
                'ref': line.cip_id.name,
                # 'date': depreciation_date or False,
                'journal_id': category_id.journal_id.id,
                'branch_id': line.cip_id.branch_id.id,
                'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
            }
            move = self.env['account.move'].create(move_vals)
            line.write({'move_id': move.id, 'move_check': True})
            created_moves |= move
            line.cip_id.state = 'in_progress'

        # if post_move and created_moves:
        #     created_moves.filtered(lambda m: any(
        #         m.asset_depreciation_ids.mapped(
        #             'asset_id.category_id.open_asset'))).post()
        return [x.id for x in created_moves]    
    
    
    
    