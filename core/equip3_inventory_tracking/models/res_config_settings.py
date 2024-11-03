
from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    expired_lot_serial_no = fields.Selection([
        ('scrap_expire', 'Immediately Scrap Expired Products'),
        ('posted', 'Creates a Transfer Operation to Expired Location'),
    ], string='Auto-Scrap Expired Products', default="scrap_expire")
    is_auto_validate = fields.Boolean(
        string="Auto-Validate Transfer Operation")
    scrap_income_id = fields.Many2one(
        comodel_name='account.account', string='Income Acccount')
    scrap_expense_id = fields.Many2one(
        comodel_name='account.account', string='Expense Acccount')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICP = self.env['ir.config_parameter'].sudo()
        res.update(
            expired_lot_serial_no=ICP.get_param(
                'expired_lot_serial_no', 'scrap_expire'),
            is_auto_validate=ICP.get_param('is_auto_validate', False),
            scrap_expense_id=int(ICP.get_param('scrap_expense_id')),
            scrap_income_id=int(ICP.get_param('scrap_income_id')),
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('expired_lot_serial_no', self.expired_lot_serial_no)
        ICP.set_param('is_auto_validate', self.is_auto_validate)
        ICP.set_param('scrap_income_id', self.scrap_income_id.id)
        ICP.set_param('scrap_expense_id', self.scrap_expense_id.id)

        usage_type_obj = self.env['usage.type'].search(
            [('name', '=', 'Auto Scrap')], limit=1)
        if usage_type_obj:
            usage_type_obj.write(
                {'account_id': self.scrap_expense_id.id, 'income_account_id': self.scrap_income_id.id})
