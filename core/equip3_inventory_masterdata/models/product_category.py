
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

ACCOUNT_DOMAIN = "['&', '&', '&', ('deprecated', '=', False), ('internal_type','=','other'), ('company_id', '=', current_company_id), ('is_off_balance', '=', False)]"

class ProductCategory(models.Model):
    _name = 'product.category'
    _inherit = ['product.category', 'mail.thread', 'mail.activity.mixin']
    
    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Product Categories'),
            'template': '/equip3_inventory_masterdata/static/src/xls/product_categories_template.xlsx'
        }]

    @api.model
    def _default_property_service_account_id(self):
        service_account_id = self.env.ref(
            'equip3_inventory_masterdata.service_expense_account_account_data', raise_if_not_found=False)
        return service_account_id and service_account_id.id or False

    product_ids = fields.One2many(
        'product.product', 'categ_id', string="Products Category")
    stock_transfer_transit_account_id = fields.Many2one('account.account', string="Stock Transfer Transit Account",
                                                        domain="[('user_type_id.name', 'ilike', 'Inventory'), ('company_id', '=', allowed_company_ids[0])]",
                                                        company_dependent=True, check_company=True,)
    stock_type = fields.Selection(
        selection=[
            ('consu', 'Consumable'),
            ('service', 'Service'),
            ('product', 'Storable Product'),
            ('asset', 'Asset'),
        ],
        default='product',
        string='Product Type',
        tracking=True
    )

    property_service_account_id = fields.Many2one(
        'account.account', string='Service Account', default=_default_property_service_account_id)
    product_limit = fields.Selection([('no_limit', "Don't Limit"), ('limit_per', 'Limit by Precentage %'), ('limit_amount', 'Limit by Amount'), (
        'str_rule', 'Strictly Limit by Purchase Order')], string='Receiving Limit', default='no_limit', tracking=True)
    min_val = fields.Integer('Minimum Value')
    max_val = fields.Integer('Maximum Value')
    delivery_limit = fields.Selection([('no_limit', "Don't Limit"), ('limit_per', 'Limit by Precentage %'), ('limit_amount', 'Limit by Amount'), (
        'str_rule', 'Strictly Limit by Sale Order')], string='Delivery Limit', default='no_limit', tracking=True)
    delivery_limit_min_val = fields.Integer('Minimum Value')
    delivery_limit_max_val = fields.Integer('Maximum Value')
    
    # override this field, giving attribute tracking=True
    property_cost_method = fields.Selection([
        ('standard', 'Standard Price'),
        ('fifo', 'First In First Out (FIFO)'),
        ('average', 'Average Cost (AVCO)')], string="Costing Method",
        company_dependent=True, copy=True, required=True, tracking=True,
        help="""Standard Price: The products are valued at their standard cost defined on the product.
        Average Cost (AVCO): The products are valued at weighted average cost.
        First In First Out (FIFO): The products are valued supposing those that enter the company first will also leave it first.
        """)
    property_valuation = fields.Selection([
        ('manual_periodic', 'Manual'),
        ('real_time', 'Automated')], string='Inventory Valuation',
        company_dependent=True, copy=True, required=True,tracking=True,
        help="""Manual: The accounting entries to value the inventory are not posted automatically.
        Automated: An accounting entry is automatically created to value the inventory when a product enters or leaves the company.
        """)
    name = fields.Char('Name', index=True, required=True, tracking=True)
    parent_id = fields.Many2one('product.category', 'Parent Category', index=True, ondelete='cascade', tracking=True)
    property_account_income_categ_id = fields.Many2one('account.account', company_dependent=True,
        string="Income Account",
        domain=ACCOUNT_DOMAIN,
        help="This account will be used when validating a customer invoice.",
        tracking=True)
    property_account_expense_categ_id = fields.Many2one('account.account', company_dependent=True,
            string="Expense Account",
            domain=ACCOUNT_DOMAIN,
            help="The expense is accounted for when a vendor bill is validated, except in anglo-saxon accounting with perpetual inventory valuation in which case the expense (Cost of Goods Sold account) is recognized at the customer invoice validation."
            ,tracking=True)
    property_account_creditor_price_difference_categ = fields.Many2one(
        'account.account', string="Price Difference Account",
        company_dependent=True,
        help="This account will be used to value price difference between purchase price and accounting cost.", tracking=True)
    property_stock_valuation_account_id = fields.Many2one(
        'account.account', 'Stock Valuation Account', company_dependent=True,
        domain="[('company_id', '=', allowed_company_ids[0]), ('deprecated', '=', False)]", check_company=True,
        help="""When automated inventory valuation is enabled on a product, this account will hold the current value of the products.""", tracking=True)
    property_stock_journal = fields.Many2one(
        'account.journal', 'Stock Journal', company_dependent=True,
        domain="[('company_id', '=', allowed_company_ids[0])]", check_company=True,
        help="When doing automated inventory valuation, this is the Accounting Journal in which entries will be automatically posted when stock moves are processed.",
        tracking=True)
    property_stock_account_input_categ_id = fields.Many2one(
        'account.account', 'Stock Input Account', company_dependent=True,
        domain="[('company_id', '=', allowed_company_ids[0]), ('deprecated', '=', False)]", check_company=True,
        help="""Counterpart journal items for all incoming stock moves will be posted in this account, unless there is a specific valuation account
                set on the source location. This is the default value for all products in this category. It can also directly be set on each product.""",
                tracking=True)
    property_stock_account_output_categ_id = fields.Many2one(
        'account.account', 'Stock Output Account', company_dependent=True,
        domain="[('company_id', '=', allowed_company_ids[0]), ('deprecated', '=', False)]", check_company=True,
        help="""When doing automated inventory valuation, counterpart journal items for all outgoing stock moves will be posted in this account,
                unless there is a specific valuation account set on the destination location. This is the default value for all products in this category.
                It can also directly be set on each product.""", tracking=True)
    


    
    
        
    @api.model
    def create(self, vals):
        res = super(ProductCategory, self).create(vals)
        cost_method_display = dict(self.fields_get(allfields=['property_cost_method'])['property_cost_method']['selection']).get(res.property_cost_method)
        valuation_display = dict(self.fields_get(allfields=['property_valuation'])['property_valuation']['selection']).get(res.property_valuation)

        mail_message = self.env['mail.message'].sudo().search([
            ('res_id', '=', res.id),
            ('model', '=', 'product.category')
        ], limit=1)
        if mail_message:
            mail_message.write({
                'body': 'Product Category created<br/> Costing Method: %s <br/> Inventory Valuation: %s' % (cost_method_display, valuation_display)
            })
        else:
            self.env['mail.message'].sudo().create({
                'subject': 'Product Category Created',
                'body': 'Product Category created<br/> Costing Method: %s <br/> Inventory Valuation: %s' % (cost_method_display, valuation_display),
                'model': 'product.category',
                'res_id': res.id,
                'message_type': 'notification',
                'subtype_id': self.env.ref('mail.mt_note').id,
            })
        return res

    @api.constrains('min_val', 'max_val', 'product_limit')
    def _onchange_value(self):
        if self.product_limit == 'limit_per' and self.min_val > 0 and self.max_val > 0 and self.min_val > self.max_val:
            raise ValidationError(
                _("Minimum value can't be more than maximum value"))

    @api.onchange('property_valuation')
    def _onchange_property_valuation(self):
        if self.property_valuation == 'real_time':
            try:
                current_company = self.env.company
                account_company = self.env.ref(
                    'equip3_inventory_masterdata.inventory_account_account_data').company_id

                if current_company.id == account_company.id:
                    self.stock_transfer_transit_account_id = self.env.ref(
                        'equip3_inventory_masterdata.inventory_account_account_data')
            except:
                self.stock_transfer_transit_account_id = False
        else:
            if not self._origin:
                return
            else:
                return {
                    'warning': {
                        'title': _("Warning"),
                        'message': _("Are you sure you want to switch to manual? By changing to manual, journal entries will not be generated when inventory movement happens.")
                    }
                }

    @api.onchange('stock_type')
    def _onchange_stock_type(self):
        if self.stock_type != 'service':
            valuation_account = self.env.ref(
                'equip3_inventory_masterdata.data_account_account_other_inventory')
            input_output_account = self.env.ref('l10n_id.a_2_900000')
            service_account_id = False
        else:
            valuation_account = self.env.ref(
                'equip3_inventory_masterdata.service_expense_account_account_data')
            input_output_account = self.env.ref(
                'equip3_inventory_masterdata.accrued_payable_account_account_data')
            service_account_id = self._default_property_service_account_id()

        self.property_stock_valuation_account_id = valuation_account.id
        self.property_stock_account_input_categ_id = input_output_account.id
        self.property_stock_account_output_categ_id = input_output_account.id
        self.property_service_account_id = service_account_id

    @api.model
    def create_product_category(self):
        product_category = self.env['product.category'].search(
            []).mapped('name')
        categ_name = [x.title() for x in product_category]
        if 'Consumable' not in categ_name:
            self.create({
                'name': 'Consumable',
                'stock_type': 'consu',
                'property_cost_method': 'standard',
                'property_valuation': 'manual_periodic',
                'category_prefix': 'CON',
                'current_sequence': '001',
            })
        if 'Service' not in categ_name:
            self.create({
                'name': 'Service',
                'stock_type': 'service',
                'property_cost_method': 'standard',
                'property_valuation': 'manual_periodic',
                'category_prefix': 'SER',
                'current_sequence': '001',
            })
        if 'Storable Product' not in categ_name:
            self.create({
                'name': 'Storable Product',
                'stock_type': 'product',
                'property_cost_method': 'standard',
                'property_valuation': 'manual_periodic',
                'category_prefix': 'STO',
                'current_sequence': '001',
            })
        if 'Asset' not in categ_name:
            self.create({
                'name': 'Asset',
                'stock_type': 'asset',
                'property_cost_method': 'standard',
                'property_valuation': 'manual_periodic',
                'category_prefix': 'AST',
                'current_sequence': '001',
            })
        return True
