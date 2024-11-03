from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mining_report_precision_rounding = fields.Integer(default=2)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res['mining_report_precision_rounding'] = int(self.env['ir.config_parameter'].sudo().get_param('equip3_mining_reports.mining_report_precision_rounding', default=2))
        return res

    @api.model
    def set_values(self):
        self.env['ir.config_parameter'].sudo().set_param('equip3_mining_reports.mining_report_precision_rounding', self.mining_report_precision_rounding)
        super(ResConfigSettings, self).set_values()

    @api.constrains('mining_report_precision_rounding')
    def _mining_report_precision_rounding_constrains(self):
        for record in self:
            if not 1 <= record.mining_report_precision_rounding <= 8:
                raise ValidationError(_('Precision rounding must between or equal to 1 and 8! (1 <= precision rounding <= 8)'))
    
    @api.model
    def set_dashboard_icon(self):
        menu_id = self.env['ir.ui.menu'].search([
            ('name', 'ilike', 'dashboard'),
            ('parent_id', '=', self.env.ref('equip3_mining_accessright_settings.mining_menu_root').id)
        ], limit=1)
        if menu_id:
            menu_id.write({'equip_icon_class': 'o-hm-sidebar-main-agriculture-dashboard-1'})