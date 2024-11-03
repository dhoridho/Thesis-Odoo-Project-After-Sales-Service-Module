# -*- coding: utf-8 -*-
from odoo import fields, models

class HrBcaBankTransferAttachment(models.TransientModel):
    _name = "hr.bca.bank.transfer.attachment"
    _description = "BCA Bank Transfer Attachment"

    attachment_file = fields.Binary('Attachment File')
    file_name = fields.Char('File Name')