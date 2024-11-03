# -*- coding: utf-8 -*-

from odoo import api, fields, models, modules, tools, _
from odoo.tools.parse_version import parse_version
from datetime import datetime, date
from odoo import tools

class IrModule(models.Model):
    _inherit = 'ir.module.module'

    version_status = fields.Selection([('updated', 'Updated'), ('not_updated', 'Not Updated'), ('not_installed', 'Not Installed')], 
                    string='Version Status', compute='_get_version_status', store=True)

    @api.depends('installed_version', 'latest_version', 'state')
    def _get_version_status(self):
        for record in self:
            if record.state != 'installed':
                record.version_status = 'not_installed'
            else:
                if record.latest_version != record.installed_version:
                    record.version_status = 'not_updated'
                elif record.latest_version == record.installed_version:
                    record.version_status = 'updated'
                else:
                    record.version_status = ''

    def button_immediate_install(self):
        for record in self:
            vals = {
                'activity_date': datetime.now(),
                'module_name': record.shortdesc,
                'technical_name': record.name,
                'latest_version': record.installed_version,
                'activity': 'install',
                'description': '',
            }
            activity_log_id = self.env['apps.installation.activity.log'].create(vals)
            if record.dependencies_id and record.dependencies_id.filtered(lambda r: r.state != 'installed'):
                for lines in record.dependencies_id.filtered(lambda r: r.state != 'installed'):
                    vals = {
                        'activity_date': datetime.now(),
                        'module_name': lines.depend_id.shortdesc,
                        'technical_name': lines.depend_id.name,
                        'latest_version': lines.depend_id.installed_version,
                        'activity': 'install',
                        'description': 'Dependency of [' + record.name + ']',
                    }
                    activity_log_id = self.env['apps.installation.activity.log'].create(vals)
        return super(IrModule, self).button_immediate_install()

    def button_immediate_upgrade(self):
        for record in self:
            vals = {
                'activity_date': datetime.now(),
                'module_name': record.shortdesc,
                'technical_name': record.name,
                'latest_version': record.latest_version,
                'activity': 'upgrade',
            }
            activity_log_id = self.env['apps.installation.activity.log'].create(vals)
        return super(IrModule, self).button_immediate_upgrade()

    def button_uninstall(self):
        for record in self:
            vals = {
                'activity_date': datetime.now(),
                'module_name': record.shortdesc,
                'technical_name': record.name,
                'latest_version': record.installed_version,
                'activity': 'try_uninstall',
            }
            activity_log_id = self.env['apps.installation.activity.log'].create(vals)
        return super(IrModule, self).button_uninstall()

    def button_uninstall_cancel(self):
        for record in self:
            vals = {
                'activity_date': datetime.now(),
                'module_name': record.shortdesc,
                'technical_name': record.name,
                'latest_version': record.installed_version,
                'activity': 'cancel_uninstall',
            }
            activity_log_id = self.env['apps.installation.activity.log'].create(vals)
        return super(IrModule, self).button_uninstall_cancel()

    def button_upgrade_cancel(self):
        for record in self:
            vals = {
                'activity_date': datetime.now(),
                'module_name': record.shortdesc,
                'technical_name': record.name,
                'latest_version': record.installed_version,
                'activity': 'cancel_upgrade',
            }
            activity_log_id = self.env['apps.installation.activity.log'].create(vals)
        return super(IrModule, self).button_upgrade_cancel()

    def button_install_cancel(self):
        for record in self:
            vals = {
                'activity_date': datetime.now(),
                'module_name': record.shortdesc,
                'technical_name': record.name,
                'latest_version': record.installed_version,
                'activity': 'cancel_install',
            }
            activity_log_id = self.env['apps.installation.activity.log'].create(vals)
        return super(IrModule, self).button_install_cancel()

class BaseModuleUpgrade(models.TransientModel):
    _inherit = "base.module.upgrade"

    def upgrade_module_cancel(self):
        for lines in self.get_module_list():
            vals = {
                'activity_date': datetime.now(),
                'module_name': lines.shortdesc,
                'technical_name': lines.name,
                'latest_version': lines.installed_version,
                'activity': 'cancel_try_uninstall',
            }
            activity_log_id = self.env['apps.installation.activity.log'].create(vals)
        return super(BaseModuleUpgrade, self).upgrade_module_cancel()

    def upgrade_module(self):
        ir_module_id = self.env['ir.module.module'].browse(self._context.get('active_ids'))
        vals = {
            'activity_date': datetime.now(),
            'module_name': ir_module_id.shortdesc,
            'technical_name': ir_module_id.name,
            'latest_version': ir_module_id.installed_version,
            'activity': 'uninstall',
            'description': '',
        }
        activity_log_id = self.env['apps.installation.activity.log'].create(vals)
        for lines in self.get_module_list():
            description = ''
            if lines.id != ir_module_id.id:
                module_name = ir_module_id.name or "module has no name"
                description = 'Depends to [' + module_name + ']'
                vals = {
                    'activity_date': datetime.now(),
                    'module_name': lines.shortdesc,
                    'technical_name': lines.name,
                    'latest_version': lines.installed_version,
                    'activity': 'uninstall',
                    'description': description,
                }
                activity_log_id = self.env['apps.installation.activity.log'].create(vals)
        return super(BaseModuleUpgrade, self).upgrade_module()


class BaseModuleUpdate(models.TransientModel):
    _inherit = "base.module.update"

    def update_module(self):
        vals = {
            'activity_date': datetime.now(),
            'module_name': 'Update Apps List',
            'technical_name': 'Update Apps List',
            'latest_version': '-',
            'activity': 'update',
        }
        activity_log_id = self.env['apps.installation.activity.log'].create(vals)
        res = super(BaseModuleUpdate, self).update_module()
        ir_modules = self.env['ir.module.module'].search([])._get_version_status()
        return res

    def cancel_update_module(self):
        vals = {
            'activity_date': datetime.now(),
            'module_name': 'Cancel Update Apps List',
            'technical_name': 'Cancel Update Apps List',
            'latest_version': '-',
            'activity': 'cancel_update',
        }
        activity_log_id = self.env['apps.installation.activity.log'].create(vals)
        return {'type': 'ir.actions.act_window_close'}

class ModuleDependency(models.Model):
    _inherit = "ir.module.module.dependency"

    installed_version = fields.Char(related='depend_id.installed_version', string='Installed Version')
    latest_version = fields.Char(related='depend_id.latest_version', string='Latest Version')