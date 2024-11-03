from odoo import api, fields, models, _


class CompanyResourceCalendar(models.Model):
    _inherit = "company.resource.calendar"

    def action_holiday_update_calendar(self):
        public_holiday = []
        Calendar = self.env["calendar.event"]
        context = self.env.context
        for comp_global_leave in self.company_global_leave_ids:
            public_holiday.append(
                {
                    "name": "Holiday" + "/" + comp_global_leave.name,
                    "start": comp_global_leave.date_from,
                    "stop": comp_global_leave.date_to,
                    "categ_ids": [
                        (
                            6,
                            0,
                            [
                                self.env.ref(
                                    "company_public_holidays_kanak.categ_meet6"
                                ).id
                            ],
                        )
                    ],
                }
            )
            
        for holiday in public_holiday:
            existing_calender = Calendar.search([("start", "=", holiday["start"])])
            if not existing_calender:
                Calendar.create(holiday)
