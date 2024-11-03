# -*- coding: utf-8 -*-
from odoo import fields, models, api

class ResConfigSettingsInherit(models.TransientModel):
    _inherit = 'res.config.settings'

    doc_pdf = fields.Boolean(string=".pdf", default=True)
    doc_xls = fields.Boolean(string=".xls", default=True)
    doc_rar = fields.Boolean(string=".rar", default=True)
    doc_doc = fields.Boolean(string=".doc", default=True)
    doc_xlsx = fields.Boolean(string=".xlsx", default=True)
    doc_mp4 = fields.Boolean(string=".mp4", default=False)
    doc_docx = fields.Boolean(string=".docx", default=True)
    doc_jpg = fields.Boolean(string=".jpg", default=False)
    doc_zip = fields.Boolean(string=".zip", default=True)
    doc_png = fields.Boolean(string=".png", default=False)
    file_size = fields.Integer(string="Maximum File Size", default=5)

    def set_values(self):
        super(ResConfigSettingsInherit, self).set_values()
        param_obj = self.env['ir.config_parameter']
        param_obj.sudo().set_param('oh_employee_documents_expiry.doc_pdf',self.doc_pdf)
        param_obj.sudo().set_param('oh_employee_documents_expiry.doc_xls',self.doc_xls)
        param_obj.sudo().set_param('oh_employee_documents_expiry.doc_rar',self.doc_rar)
        param_obj.sudo().set_param('oh_employee_documents_expiry.doc_doc',self.doc_doc)
        param_obj.sudo().set_param('oh_employee_documents_expiry.doc_xlsx',self.doc_xlsx)
        param_obj.sudo().set_param('oh_employee_documents_expiry.doc_mp4',self.doc_mp4)
        param_obj.sudo().set_param('oh_employee_documents_expiry.doc_docx',self.doc_docx)
        param_obj.sudo().set_param('oh_employee_documents_expiry.doc_jpg',self.doc_jpg)
        param_obj.sudo().set_param('oh_employee_documents_expiry.doc_zip',self.doc_zip)
        param_obj.sudo().set_param('oh_employee_documents_expiry.doc_png',self.doc_png)
        param_obj.sudo().set_param('oh_employee_documents_expiry.file_size',self.file_size)

    @api.model
    def get_values(self):
        res = super(ResConfigSettingsInherit, self).get_values()
        param_obj = self.env['ir.config_parameter']
        res.update(doc_pdf=param_obj.sudo().get_param('oh_employee_documents_expiry.doc_pdf',default=True),
                   doc_xls=param_obj.sudo().get_param('oh_employee_documents_expiry.doc_xls',default=True),
                   doc_rar=param_obj.sudo().get_param('oh_employee_documents_expiry.doc_rar',default=True),
                   doc_doc=param_obj.sudo().get_param('oh_employee_documents_expiry.doc_doc',default=True),
                   doc_xlsx=param_obj.sudo().get_param('oh_employee_documents_expiry.doc_xlsx',default=True),
                   doc_mp4=param_obj.sudo().get_param('oh_employee_documents_expiry.doc_mp4',default=False),
                   doc_docx=param_obj.sudo().get_param('oh_employee_documents_expiry.doc_docx',default=True),
                   doc_jpg=param_obj.sudo().get_param('oh_employee_documents_expiry.doc_jpg',default=False),
                   doc_zip=param_obj.sudo().get_param('oh_employee_documents_expiry.doc_zip',default=True),
                   doc_png=param_obj.sudo().get_param('oh_employee_documents_expiry.doc_png',default=False),
                   file_size=param_obj.sudo().get_param('oh_employee_documents_expiry.file_size',default=5),
                   )
        return res