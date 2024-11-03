# -*- coding: utf-8 -*-

from odoo import models, fields, api, SUPERUSER_ID

class ir_ui_menu(models.Model):
    _inherit = 'ir.ui.menu'
    
    def search(self, args, offset=0, limit=None, order=None, count=False):
        if self.env.user and not self.env.user.has_group('base.group_portal'):
            student_group_model, group_school_parent = self.env['ir.model.data'].get_object_reference('school', 'group_school_parent')
            student_group_model, group_school_student = self.env['ir.model.data'].get_object_reference('school', 'group_school_student')
            if group_school_parent or group_school_student:
                group_schools = self.env[str(student_group_model)].sudo().browse([group_school_parent, group_school_student])
                if group_schools:
                    user_all_ids = [us.id for us in group_schools.users]
                    if self._uid in user_all_ids:
                        args.append(('id','in',[]))
                        return super(ir_ui_menu, self).search(args, offset, limit, order, count=count)
        return super(ir_ui_menu, self).search(args, offset, limit, order, count=count)
