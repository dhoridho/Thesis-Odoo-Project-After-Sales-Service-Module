from odoo import api, fields, models,tools, SUPERUSER_ID , _
from odoo.addons.base.models.res_partner import _tz_get


class HrLeaveReportCalendarInherit(models.Model):
    _inherit = 'hr.leave.report.calendar'

    leave_type = fields.Many2one("hr.leave.type", string="Leave Type")

    def init(self):
        tools.drop_view_if_exists(self._cr, 'hr_leave_report_calendar')
        self._cr.execute("""CREATE OR REPLACE VIEW hr_leave_report_calendar AS
        (SELECT 
            row_number() OVER() AS id,
            CONCAT(em.name, ': ', hl.duration_display) AS name,
            hl.date_from AS start_datetime,
            hl.date_to AS stop_datetime,
            hl.employee_id AS employee_id,
            hl.state AS state,
            hl.holiday_status_id AS leave_type,
            em.company_id AS company_id,
            CASE
                WHEN hl.holiday_type = 'employee' THEN rr.tz
                ELSE %s
            END AS tz
        FROM hr_leave hl
            LEFT JOIN hr_employee em
                ON em.id = hl.employee_id
            LEFT JOIN resource_resource rr
                ON rr.id = em.resource_id
        WHERE 
            hl.state IN ('confirm', 'validate', 'validate1')
        ORDER BY id);
        """, [self.env.company.resource_calendar_id.tz or self.env.user.tz or 'UTC'])
    
    def custom_menu(self):
        # views = [(self.env.ref('bi_employee_travel_managment.view_travel_req_tree').id, 'tree'),
        #              (self.env.ref('bi_employee_travel_managment.view_travel_req_form').id, 'form')]
    # search_view_id = self.env.ref("hr_contract.hr_contract_view_search")
        if  self.env.user.has_group('equip3_hr_employee_access_right_setting.group_responsible') and not self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
            employee_ids = []
            my_employee = self.env['hr.employee'].sudo().search([('user_id','=',self.env.user.id)])
            if my_employee:
                for child_record in my_employee.child_ids:
                    employee_ids.append(my_employee.id)
                    employee_ids.append(child_record.id)
                    child_record._get_amployee_hierarchy(employee_ids,child_record.child_ids,my_employee.id)
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'All Time Off',
                    'res_model': 'hr.leave.report.calendar',
                    'target':'current',
                    'view_mode': 'calendar',
                    # 'views':views,
                    'domain': [('employee_id', 'in', employee_ids),('employee_id.active','=',True)],
                    'context':{'hide_employee_name': 1},
                    'help':"""<p class="o_view_nocontent_smiling_face">
                        Create a new All Time Off
                    </p>"""
                    # 'context':{'search_default_current':1, 'search_default_group_by_state': 1},
                    # 'search_view_id':search_view_id.id,
                    
                }
        
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'All Time Off',
                'res_model': 'hr.leave.report.calendar',
                'target':'current',
                'view_mode': 'calendar',
                'domain': [('employee_id.active','=',True)],
                'help':"""<p class="o_view_nocontent_smiling_face">
                    Create a new All Time Off
                </p>""",
                'context':{'hide_employee_name': 1},
                # 'views':views,
                # 'search_view_id':search_view_id.id,
            }
