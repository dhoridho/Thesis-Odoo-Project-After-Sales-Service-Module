from werkzeug import urls

from odoo import api, fields, models
from odoo.exceptions import ValidationError

class HrRecruitmentOutourceMaster(models.Model):
    _name = 'hr.recruitment.outsource.master'
    _description="HR Recruitment Outsource Master"

    name = fields.Char("Name")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company.id)

class HrRecruitmentOutource(models.Model):
    _name = 'hr.recruitment.outsource'
    _description="HR Recruitment Outsource"

    outsource_id = fields.Many2one('hr.recruitment.outsource.master', string="Outsource", required=True)
    job_id = fields.Many2one('hr.job', string="Job", required=True)
    responsible_user_id = fields.Many2one('res.users', string="Responsible Users")
    url = fields.Char(string="Url Parameter")

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, record.outsource_id.name))
        return result
    
    def generate_link(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            if rec.job_id.state == "open":
                raise ValidationError("Selected Job Position are not in Recruitment Progress. Please select another Job Position")
            rec.url = urls.url_join(base_url, "jobs/apply/%s?%s" % (rec.job_id.id,
                urls.url_encode({
                    'outsource': rec.outsource_id.id
                })
            ))