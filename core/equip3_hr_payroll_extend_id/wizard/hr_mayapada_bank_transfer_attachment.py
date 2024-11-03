# -*- coding: utf-8 -*-
from odoo import fields, models

class HrMayapadaBankTransferAttachment(models.TransientModel):
    _name = "hr.mayapada.bank.transfer.attachment"
    _description = "Mayapada Bank Transfer Attachment"

    attachment_file = fields.Binary('Attachment File')
    file_name = fields.Char('File Name')