from odoo import api,fields,models

class evaResUsers(models.Model):
    _inherit = 'res.users'
    
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        user_job = self.env.ref('equip3_eva_jobportal_integration.admin_integration_job_portal').id
        if user_job:
            domain.append(('id', '!=', user_job))

        return super(evaResUsers, self).search_read(domain, fields, offset, limit, order)


    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        user_job = self.env.ref('equip3_eva_jobportal_integration.admin_integration_job_portal').id
        if user_job:
            domain.append(('id', '!=', user_job))

            
        return super(evaResUsers, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                           orderby=orderby, lazy=lazy)