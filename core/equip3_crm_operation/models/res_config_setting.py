
from odoo import models, fields, api

class ResConfigSetting(models.TransientModel):
    _inherit = 'res.config.settings'

    group_use_multi_salesperson_on_leads = fields.Boolean(string="Multi Salesperson", implied_group='equip3_crm_operation.group_use_multi_salesperson_on_leads')
    is_auto_follow_up = fields.Boolean(string="Auto Follow Up")
    interval_number = fields.Integer(string="Execute Every")
    interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')
        ])
    number_of_repetition = fields.Integer(string="Number of Repetitions")
    
    @api.model
    def get_values(self):
        res = super(ResConfigSetting, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        res.update({
            'is_auto_follow_up': IrConfigParam.get_param('equip3_crm_operation.is_auto_follow_up'),
            'module_crm_iap_lead_website': False,
            'module_crm_iap_lead_enrich': False,
            'module_crm_iap_lead': False,
            'module_mail_client_extension': False,
        })
        return res
    
    def set_values(self):
        super(ResConfigSetting, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('equip3_crm_operation.is_auto_follow_up', self.is_auto_follow_up)
        self.env["ir.config_parameter"].sudo().set_param("crm.module_crm_iap_lead_website", False)
        self.env["ir.config_parameter"].sudo().set_param("crm.module_crm_iap_lead_enrich", False)
        self.env["ir.config_parameter"].sudo().set_param("crm.module_crm_iap_lead", False)
        self.env["ir.config_parameter"].sudo().set_param("crm.module_mail_client_extension", False)

        if self.is_auto_follow_up:
            cron = self.env.ref('equip3_crm_operation.auto_follow_up_leads_sales_team').active = True
        else:
            cron = self.env.ref('equip3_crm_operation.auto_follow_up_leads_sales_team').active = False
