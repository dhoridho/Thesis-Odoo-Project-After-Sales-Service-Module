# -*- coding: utf-8 -*-
from odoo import fields, models

class HrSptReport1721IAttachment(models.TransientModel):
    _name = "hr.spt.report.1721_i.attachment"
    _description = "1721 I Attachment"

    attachment_file = fields.Binary('Attachment File')
    file_name = fields.Char('File Name')