from odoo import models, fields, api, _
from odoo.tools import float_is_zero
from odoo.osv import expression

COST_ACT_ACCOUNT_TYPES = [
    'account.data_account_type_payable',
    'account.data_account_type_credit_card',
    'account.data_account_type_current_liabilities',
    'account.data_account_type_non_current_liabilities',
    'account.data_account_type_expenses'
]


class ProductTemlateInherit(models.Model):
    _inherit = 'product.template'

    @api.model
    def _default_allowed_manuf_account_types(self):
        return [(6, 0, [self.env.ref(xml_id).id for xml_id in COST_ACT_ACCOUNT_TYPES])]

    def _compute_allowed_manuf_account_types(self):
        self.allowed_manuf_account_type_ids = self._default_allowed_manuf_account_types()

    manuf_cost = fields.Boolean('Is Manufacturing Cost')
    manuf_cost_category = fields.Selection(
        selection=[('material', 'Material'), ('overhead', 'Overhead'), ('labor', 'Labor')],
        string='Cost Category'
    )

    allowed_manuf_account_type_ids = fields.Many2many('account.account.type', compute=_compute_allowed_manuf_account_types, default=_default_allowed_manuf_account_types)
    manuf_account_id = fields.Many2one('account.account', string='Account', domain="[('user_type_id', 'in', allowed_manuf_account_type_ids)]")

    overhead_cost = fields.Boolean('Overhead Cost', default=False)

    @api.onchange('type')
    def onchange_product_type(self):
        if self.type == 'product' and self.overhead_cost:
            self.overhead_cost = False
