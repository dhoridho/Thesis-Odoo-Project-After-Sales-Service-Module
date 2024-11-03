
from odoo import api , fields , models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        if self.is_pr_department:
            self.env.ref("equip3_purchase_report.menu_purchase_type").write({
                "action": self.env.ref("equip3_purchase_report.action_purchase_request_report")
            })
        else:
            self.env.ref("equip3_purchase_report.menu_purchase_type").write({
                "action": self.env.ref("equip3_purchase_report.action_purchase_request_report_2")
            })
        return res

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        if IrConfigParam.get_param('is_pr_department'):
            self.env.ref("equip3_purchase_report.menu_purchase_type").write({
                "action": self.env.ref("equip3_purchase_report.action_purchase_request_report")
            })
        else:
            self.env.ref("equip3_purchase_report.menu_purchase_type").write({
                "action": self.env.ref("equip3_purchase_report.action_purchase_request_report_2")
            })
        return res