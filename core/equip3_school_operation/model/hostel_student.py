# from odoo import _, api, fields, models
# from datetime import date, timedelta
#
# class HostelStudent(models.Model):
#     _inherit = "hostel.student"
#
#     def reservation_state(self):
#         sequence_obj = self.env["ir.sequence"]
#         for rec in self:
#             if rec.hostel_id == "New":
#                 rec.hostel_id = sequence_obj.next_by_code(
#                     "hostel.new.student"
#                 ) or _("New")
#             rec.status = "reservation"
#
#     def pay_fees(self):
#         res = super(HostelStudent, self).pay_fees()
#         for rec in self:
#             invoice_ids = self.env['account.move'].search([('hostel_student_id', '=', rec.id)], limit=1)
#             invoice_ids.write({
#                 'partner_id': rec.student_id.user_id.partner_id.id,
#                 'invoice_date': date.today(),
#             })
#         return res
#
