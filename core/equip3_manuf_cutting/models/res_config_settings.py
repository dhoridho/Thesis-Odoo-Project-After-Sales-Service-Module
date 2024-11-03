from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_cutting_plan = fields.Boolean(string='Cutting Plan', related='company_id.is_cutting_plan', readonly=False)
    is_cutting_order = fields.Boolean(string='Cutting Order', related='company_id.is_cutting_order', readonly=False)
    send_whatsapp_notif_cp = fields.Boolean(config_parameter='equip3_manuf_cutting.send_whatsapp_notif_cp')
    send_whatsapp_notif_co = fields.Boolean(config_parameter='equip3_manuf_cutting.send_whatsapp_notif_co')

    @api.onchange('is_cutting_plan')
    def onchange_is_cutting_plan(self):
        if not self.is_cutting_plan:
            self.send_whatsapp_notif_cp = False

    @api.onchange('is_cutting_order')
    def onchange_is_cutting_order(self):
        if not self.is_cutting_order:
            self.send_whatsapp_notif_co = False
