from odoo import models,api
from odoo.exceptions import ValidationError

class resUsersInherit(models.Model):
    _inherit = 'res.users'
    
    @api.model
    def create(self, vals_list):
        res =  super(resUsersInherit,self).create(vals_list)
        if self.env.user.has_group('equip3_hr_accessright_settings.equip3_group_hr_recruitment_manager') and not self.env.user.has_group('hr_recruitment.group_hr_recruitment_manager'):
            if res.access_rights_profile_id.id  == self.env.ref("equip3_hr_eva_recruitment.profile_admin").id:
                raise ValidationError("Manager Cannot Create Super admin")
        return res
    
    # @api.onchange('access_rights_profile_id')
    # def _onchange_access_rights_profile_id(self):
    #     for record in self:
    #         if record.access_rights_profile_id:
    #             if self.env.user.has_group('equip3_hr_accessright_settings.equip3_group_hr_recruitment_manager'):
    #                 if record.access_rights_profile_id.id == self.env.ref("equip3_hr_eva_recruitment.profile_admin").id:
    #                     raise ValidationError("Manager edit to super admin")
                        
    
    
    def write(self,vals):
        if self.env.user.has_group('equip3_hr_accessright_settings.equip3_group_hr_recruitment_manager') and not self.env.user.has_group('hr_recruitment.group_hr_recruitment_manager'):
            if 'access_rights_profile_id' in vals:
                if vals['access_rights_profile_id'] == self.env.ref("equip3_hr_eva_recruitment.profile_admin").id:
                    raise ValidationError("Manager Cannot edit to Super admin")
            if self.access_rights_profile_id.id == self.env.ref("equip3_hr_eva_recruitment.profile_admin").id:
                raise ValidationError("Manager Cannot create/edit Super admin")
        res =  super(resUsersInherit,self).write(vals)
        return res
    
    def unlink(self):
        if self.env.user.has_group('equip3_hr_accessright_settings.equip3_group_hr_recruitment_manager') and not self.env.user.has_group('hr_recruitment.group_hr_recruitment_manager'):
            if self.access_rights_profile_id.id  == self.env.ref("equip3_hr_eva_recruitment.profile_admin").id:
                raise ValidationError("Manager Cannot create/edit Super admin")
        res =  super(resUsersInherit,self).unlink()
        return res