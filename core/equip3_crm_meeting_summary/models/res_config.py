from odoo import models,fields,api


class ResConfigInherit(models.TransientModel):
    _inherit = 'res.config.settings'

    is_meeting_summary = fields.Boolean(string='Meeting Summary',
        config_parameter='equip3_crm_meeting_summary.is_meeting_summary')
    is_use_template_meeting_summary = fields.Boolean(string='Use Template in Meeting Summary',
        config_parameter='equip3_crm_meeting_summary.is_use_template_meeting_summary')

    @api.model
    def get_values(self):
        res = super(ResConfigInherit, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        if IrConfigParam.get_param('is_meeting_summary', False):
            is_use_template_meeting_summary = IrConfigParam.get_param('is_use_template_meeting_summary', False)
        else:
            is_use_template_meeting_summary = False
        res.update({
            'is_meeting_summary': IrConfigParam.get_param('is_meeting_summary', False),
            'is_use_template_meeting_summary': is_use_template_meeting_summary,
        })
        return res
    
    def set_values(self):
        super(ResConfigInherit, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('is_meeting_summary', self.is_meeting_summary)
        if self.is_meeting_summary:
            self.env['ir.config_parameter'].sudo().set_param('is_use_template_meeting_summary', self.is_use_template_meeting_summary)
        else:
            self.env['ir.config_parameter'].sudo().set_param('is_use_template_meeting_summary', False)
        
        if self.is_meeting_summary:
            self.env.ref("equip3_crm_meeting_summary.summary_template_menu_act").active = True
        else:
            self.env.ref("equip3_crm_meeting_summary.summary_template_menu_act").active = False