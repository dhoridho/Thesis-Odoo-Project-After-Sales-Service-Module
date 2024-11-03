from odoo import _, api, fields, models

class StudentCertificate(models.Model):
    _inherit = "student.certificate"

    certi = fields.Binary(attachment=True, store=True)
    file_name = fields.Char(string="File Name")
