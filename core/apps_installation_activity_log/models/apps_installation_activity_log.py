# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class AppsInstallationActivityLog(models.Model):
    _name = 'apps.installation.activity.log'
    _rec_name = 'module_name'

    activity_date = fields.Datetime(string='Activity Date', readonly=True)
    module_name = fields.Char(string='Module Name', readonly=True)
    technical_name = fields.Char(string='Technical Name', readonly=True)
    latest_version = fields.Char(string='Latest Version', readonly=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user.id)
    activity = fields.Selection([('install', 'Install'), ('upgrade', 'Upgrade'), 
                ('try_uninstall', 'Try to Uninstall'), ('uninstall', 'Uninstall'), ('cancel_uninstall', 'Cancel Uninstall'), 
                ('cancel_upgrade', 'Cancel Upgrade'), ('cancel_install', 'Cancel Install'), 
                ('cancel_try_uninstall', 'Cancel Try to Uninstall'),('update','Update Apps List'),('cancel_update','Cancel Update App List'), ('close_uninstall_wizard', 'Close Uninstall Wizard')], 
                string='Activity', readonly=True)
    description = fields.Text(string='Description')