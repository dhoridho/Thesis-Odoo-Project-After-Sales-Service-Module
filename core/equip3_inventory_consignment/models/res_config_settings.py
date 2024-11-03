from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    commision_consignment = fields.Selection([('cash_commision', 'Cash Commision'),
                                      ('accrued_commision', 'Accrued Commision')],
                                      string="Commision Consignment")
    consignment_commision_account = fields.Many2one('account.account', 'Consignment Commision',
                                                    domain="[('deprecated', '=', False), ('company_id', '=', company_id),('user_type_id.type','not in', ('receivable','payable')),('is_off_balance', '=', False)]")
    accrued_commision_account = fields.Many2one('account.account', 'Accrued Commision',
                                                domain="[('deprecated', '=', False), ('company_id', '=', company_id),('user_type_id.type','not in', ('receivable','payable')),('is_off_balance', '=', False)]")

    @api.onchange('commision_consignment')
    def onchange_commision_consignment(self):
        if self.commision_consignment == 'cash_commision':
            self.accrued_commision_account = False

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICP = self.env['ir.config_parameter'].sudo()
        commision_consignment = ICP.get_param(key='commision_consignment', default='accrued_commision')
        res.update(
            commision_consignment=commision_consignment,
            consignment_commision_account=int(ICP.get_param('consignment_commision_account', False)),
            accrued_commision_account=int(ICP.get_param('accrued_commision_account', False)),
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        IrConfigParam.set_param('commision_consignment', self.commision_consignment)
        IrConfigParam.set_param('consignment_commision_account', self.consignment_commision_account.id)
        IrConfigParam.set_param('accrued_commision_account', self.accrued_commision_account.id)
