from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
from lxml import etree

class HrPtkpChangeStatus(models.Model):
    _name = 'hr.ptkp.change.status'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    hr_years = fields.Many2one('hr.years', string='HR Years', required=True, domain=[('status','=','open')])
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    sequence_code = fields.Char('Employee ID', readonly=True)
    department_id = fields.Many2one('hr.department', string='Department', readonly=True)
    job_id = fields.Many2one('hr.job', string='Job Position', readonly=True)
    ptkp_id = fields.Many2one('hr.tax.ptkp', string='PTKP Status', readonly=True)
    new_ptkp_id = fields.Many2one('hr.tax.ptkp', string='New PTKP Status', required=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('confirmed', 'Confirmed'), ('updated', 'Updated')], string='Status', tracking=True, default='draft')
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(HrPtkpChangeStatus, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if  self.env.user.has_group('hr.group_hr_user') and not self.env.user.has_group('hr.group_hr_manager') :
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    def unlink(self):
        for rec in self:
            if rec.state not in ('draft'):
                raise UserError(_('Cannot delete data which are already confirmed.'))
        return super(HrPtkpChangeStatus, self).unlink()

    @api.constrains('hr_years', 'employee_id')
    def check_employee(self):
        for record in self:
            if record.hr_years and record.employee_id:
                now = datetime.now()
                current_date = now.date()
                current_year = current_date.year
                hr_year = datetime.strptime(str(record.hr_years.start_date), '%Y-%m-%d').date().year

                if hr_year <= current_year:
                    raise ValidationError("HR Years must be next year!")

                check_employee = self.search([('hr_years', '=', record.hr_years.id),
                                              ('employee_id', '=', record.employee_id.id),
                                              ('id', '!=', record.id)])
                if check_employee:
                    raise ValidationError("Employee has been created in same years!")

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for res in self:
            if res.employee_id:
                res.sequence_code = res.employee_id.sequence_code
                res.department_id = res.employee_id.department_id.id
                res.job_id = res.employee_id.job_id.id
                res.ptkp_id = res.employee_id.ptkp_id.id

    def action_confirm(self):
        self.state = 'confirmed'

    def action_draft(self):
        self.state = 'draft'

    def change_ptkp_status(self):
        now = datetime.now()
        date_now = now.date()
        data = self.search([('state','=','confirmed')])
        for rec in data:
            if date_now >= rec.hr_years.start_date:
                employee = self.env['hr.employee'].sudo().search([('id','=',rec.employee_id.id)], limit=1)
                employee.ptkp_id = rec.new_ptkp_id.id
                rec.state = 'updated'
