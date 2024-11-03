# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class HrPesangonUpmkSettings(models.Model):
    _name = 'hr.pesangon.upmk.settings'
    _description = 'Pesangon & UPMK Settings'

    name = fields.Char("Name", required=True, readonly=True)
    pesangon_setting_ids = fields.One2many('hr.pesangon.setting.line', 'parent_id')
    upmk_setting_ids = fields.One2many('hr.upmk.setting.line', 'parent_id')

    def mass_update_pesangon(self):
        action = self.env.ref('equip3_hr_payroll_extend_id.action_mass_update_pesangon_setting').read()[0]
        return action

    def mass_update_upmk(self):
        action = self.env.ref('equip3_hr_payroll_extend_id.action_mass_update_upmk_setting').read()[0]
        return action

class HrPesangonSettingLine(models.Model):
    _name = 'hr.pesangon.setting.line'

    parent_id = fields.Many2one("hr.pesangon.upmk.settings")
    year_of_services = fields.Float(string="Years Of Service")
    value = fields.Float(string="Values")
    salary_rules = fields.Many2many('hr.salary.rule', string="Salary Rules")

class HrUpmkSettingLine(models.Model):
    _name = 'hr.upmk.setting.line'

    parent_id = fields.Many2one("hr.pesangon.upmk.settings")
    year_of_services = fields.Float(string="Years Of Service")
    value = fields.Float(string="Values")
    salary_rules = fields.Many2many('hr.salary.rule', string="Salary Rules")

class MassUpdatePesangonSetting(models.TransientModel):
    _name = 'mass.update.pesangon.setting'

    parent_id = fields.Many2one("hr.pesangon.upmk.settings")
    salary_rules = fields.Many2many('hr.salary.rule', string="Salary Rules")


    def update_mass(self):
        active_id = self.env.context.get('active_ids')
        for res in self.parent_id.browse(active_id):
            for mass in res.pesangon_setting_ids:
                mass.salary_rules = self.salary_rules.ids

class MassUpdateUpmkSetting(models.TransientModel):
    _name = 'mass.update.upmk.setting'

    parent_id = fields.Many2one("hr.pesangon.upmk.settings")
    salary_rules = fields.Many2many('hr.salary.rule', string="Salary Rules")


    def update_mass(self):
        active_id = self.env.context.get('active_ids')
        for res in self.parent_id.browse(active_id):
            for mass in res.upmk_setting_ids:
                mass.salary_rules = self.salary_rules.ids