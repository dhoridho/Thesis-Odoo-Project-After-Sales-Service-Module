from odoo import models, fields, api
from odoo.exceptions import ValidationError



class HashMicroConfigSettings(models.Model):
    _name = 'expiry.contract.notification'
    name = fields.Char()
    month = fields.Integer()
    days = fields.Integer()
    company_id = fields.Many2one('res.company',default=lambda self:self.company_id.id)
    line_ids = fields.One2many('expiry.contract.notification.line', 'notification_id', string='Lines')


    def unlink(self):
        if self.name:
            return ValidationError("Can't delete record")
        res=super(HashMicroConfigSettings, self).unlink()
        return  res
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HashMicroConfigSettings, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HashMicroConfigSettings, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)




    def send_notification(self,type,ids):
        if type == "contract_expire":
            action_id = self.env.ref('equip3_hr_contract_extend.contract_expire_action')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') + (
                    "/web?&#min=1&limit=80&view_type=list&model=hr.contract&action=%s" % (action_id.id))
            template = self.env.ref('equip3_hr_contract_extend.mail_template_contract_expired')
            contract_obj = self.env['hr.contract'].browse(ids)
            for line in self.line_ids:
                for job in line.job_ids:
                    for pic in line.pic_ids:
                        _lines = []
                        for contract in contract_obj:
                            if contract.job_id == job:
                                pic_names = []
                                for pic_name in line.pic_ids:
                                    pic_names.append(pic_name.name)
                                pic_names = ', '.join(pic_names)
                                _lines.append({
                                    'employee_name': contract.employee_id.name,
                                    'contract_ref': contract.name,
                                    'job_position': contract.job_id.name,
                                    'contract_expired': contract.date_end.strftime('%d-%m-%Y'),
                                    'pic_name': pic_names,
                                })
                        if _lines:
                            context = self.env.context = dict(self.env.context)
                            context.update({
                                'email_to': pic.work_email,
                                'name': pic.name,
                                'lines': _lines,
                                'url_contract': base_url,
                            })
                            template.send_mail(pic.id, force_send=True)
                            template.with_context(context)
        if type == "contract_renew":
            action_id = self.env.ref('equip3_hr_contract_extend.contract_running_action')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') + (
                    "/web?&#min=1&limit=80&view_type=list&model=hr.contract&action=%s" % (action_id.id))
            template = self.env.ref('equip3_hr_contract_extend.mail_template_contract_to_renew')
            contract_obj = self.env['hr.contract'].browse(ids)
            for line in self.line_ids:
                for job in line.job_ids:
                    for pic in line.pic_ids:
                        _lines = []
                        for contract in contract_obj:
                            if contract.job_id == job:
                                pic_names = []
                                for pic_name in line.pic_ids:
                                    pic_names.append(pic_name.name)
                                pic_names = ', '.join(pic_names)
                                _lines.append({
                                    'employee_name': contract.employee_id.name,
                                    'contract_ref': contract.name,
                                    'job_position': contract.job_id.name,
                                    'contract_expired': contract.date_end.strftime('%d-%m-%Y'),
                                    'pic_name': pic_names,
                                })
                        if _lines:
                            context = self.env.context = dict(self.env.context)
                            context.update({
                                'email_to': pic.work_email,
                                'name': pic.name,
                                'lines': _lines,
                                'url_contract': base_url,
                            })
                            template.send_mail(pic.id, force_send=True)
                            template.with_context(context)
    
    @api.constrains('line_ids')
    def _constrains_notification_line(self):
        for rec in self:
            jobs = []
            pic_lines = []
            for line in rec.line_ids:
                for line_job in line.job_ids:
                    if line_job.id in jobs:
                        raise ValidationError("You can't to set same Job Position in another line")
                    jobs.append(line_job.id)
                for line_pic in line.pic_ids:
                    if line_pic.id in pic_lines:
                        raise ValidationError("You can't to set same PIC in another line")
                    pic_lines.append(line_pic.id)

class ExpiryContractNotificationLine(models.Model):
    _name = 'expiry.contract.notification.line'
    _description = 'Expiry Contract Notification Line'

    notification_id = fields.Many2one('expiry.contract.notification', string='Contract Notification')
    job_ids = fields.Many2many('hr.job',string="Job Position", required=True)
    pic_ids = fields.Many2many('hr.employee',string="PIC", required=True)
    