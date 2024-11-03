from odoo import SUPERUSER_ID, _, api, fields, models,tools
from collections import defaultdict
import os
import re

directory = os.path.dirname(__file__)


class IrModel(models.Model):
    _inherit = 'ir.model'


    is_use_tracking_log = fields.Boolean("Tracking Log",compute="_compute_is_use_tracking_log",inverse=False)
    is_manual_use_tracking_log = fields.Boolean('Manual Use Tracking Log',copy=False,default=False)
    is_already_create_inherit_views = fields.Boolean('Already Create Inherit Views',copy=False,default=False)

    def _compute_is_use_tracking_log(self):
        for data in self:
            is_use_tracking_log = False
            if data.is_mail_thread and data.is_mail_activity :
                is_use_tracking_log = True
            fields_name = data.field_id.mapped('name')
            if 'message_ids' in fields_name and 'activity_ids' in fields_name:
                is_use_tracking_log = True

            data.is_use_tracking_log = is_use_tracking_log


    def set_active_tracking_log(self):
        self.ensure_one()
        fields_obj = self.env['ir.model.fields']
        apps_obj = self.env['ir.module.module']
        view_obj = self.env['ir.ui.view'].sudo()
        data = self
        name_model = data.model
        model = self.env[name_model]
        # self.env.cr.execute('UPDATE ir_model SET is_mail_thread=%s, is_mail_activity=%s WHERE id=%s', (True,True,data.id,))
        self.env.cr.execute('UPDATE ir_model SET is_manual_use_tracking_log=%s WHERE id=%s', (True,data.id,))

        parents = model._inherit or []
        parents = [parents] if isinstance(parents, str) else parents
        new_parent = [name_model]
        if 'mail.thread' not in parents:
            new_parent.append('mail.thread')
        if 'mail.activity.mixin' not in parents:
            new_parent.append('mail.activity.mixin')

        parents = new_parent

        if parents:
            xmlid = self.get_external_id()
            name_module_write = 'equip3_tracking_logs_inherit'
            name_module = xmlid[self.id].split('.')[0]
            directory_module = directory.split('equip3_tracking_logs')[0]
            directory_module = directory_module +name_module_write
            new_depends_str = "    'depends': "
            with open(os.path.join(directory_module, '__manifest__.py')) as file_manifest_content:
                file_manifest = file_manifest_content.readlines()
            get_depends = re.search(r'\[(.*?)\]', file_manifest[6])
            get_depends = get_depends.group(0)
            get_depends = eval(get_depends)
            get_depends.append(name_module)
            new_depends = get_depends
            file_manifest[6] = new_depends_str + str(new_depends) +',\n'
            with open(os.path.join(directory_module, '__manifest__.py'), "w") as new_file_manifest:
                new_file_manifest.writelines(file_manifest)

            with open(os.path.join(directory_module, '__manifest__.py'), 'r') as new_file_manifest:
                code = new_file_manifest.read()
            exec(code)

            name_parent_class = 'class '+name_model.replace('.','_')+'(models.Model):'
            name_class = "    _name = "+"'"+name_model+"'"
            name_inherit = "    _inherit = "+str(parents)
            file_py =  open(os.path.join(directory_module+'/models', 'all_models.py'), 'a')
            file_py.write(name_parent_class+"\n")
            file_py.write(name_class+"\n")
            file_py.write(name_inherit+"\n\n\n\n")
            with open(os.path.join(directory_module+'/models', 'all_models.py'), 'r') as file_py:
                code = file_py.read()
            exec(code)


            this_module = apps_obj.sudo().search([('name','=',name_module_write)])
            return this_module.button_immediate_upgrade()


        return True
                    



    def set_inactive_tracking_log(self):
        self.ensure_one()
        self.field_id.write({'is_manually_set_tracking':False})
        return True


class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'


    is_manually_set_tracking = fields.Boolean("Manually Set Tracking ?",compute="_compute_is_manually_set_tracking",inverse='_inverse_is_manually_set_tracking')
    is_manual_tracking = fields.Boolean()


    def _compute_is_manually_set_tracking(self):
        for data in self:
            is_manually_set_tracking = False
            if data.tracking == 100 or data.is_manual_tracking:
                is_manually_set_tracking = True
            data.is_manually_set_tracking = is_manually_set_tracking


    def _inverse_is_manually_set_tracking(self):
        for data in self:
            if data.is_manually_set_tracking:
                tracking = 100
            else:
                tracking = 0
            data.tracking = tracking



    def write(self, vals):
        view_obj = self.env['ir.ui.view'].sudo()
        if 'is_manually_set_tracking' in vals:
            tracking = 0
            is_manual_tracking = False
            if vals['is_manually_set_tracking']:
                tracking = 100
                is_manual_tracking = True
            for data in self:
                self.env.cr.execute('UPDATE ir_model_fields SET tracking=%s, is_manual_tracking=%s WHERE id=%s', (tracking,is_manual_tracking,data.id,))
                if not data.model_id.is_already_create_inherit_views and data.model_id.is_manual_use_tracking_log:
                    views = view_obj.search([('model','=',data.model_id.model),('type','=','form'),('mode','=','primary'),('xml_id','!=',False)])
                    if views:
                        self.env.cr.execute('UPDATE ir_model SET is_already_create_inherit_views=%s WHERE id=%s', (True,data.model_id.id,))
                        for view in views:
                            name_view = 'inherit_id_'+str(view.id)
                            arch = '<?xml version="1.0"?>'
                            arch+= '<data>'
                            arch+= '''<xpath expr="//form" position="inside">
                                    <div class="oe_chatter">
                                        <field name="message_follower_ids"/><field name="activity_ids"/><field name="message_ids"/>
                                    </div>
                                </xpath>'''
                            arch+= '</data>'
                            view_obj.create({
                                'type':'form',
                                'name':name_view,
                                'model':data.model_id.model,
                                'mode':'extension',
                                'arch':arch,
                                'inherit_id':view.id,
                            })
            vals = {}
        res = super(IrModelFields, self).write(vals)
        return res
