# -*- coding: utf-8 -*-
from odoo import fields, models

class HrDanamonBankTransferAttachment(models.TransientModel):
    _name = "hr.danamon.bank.transfer.attachment"
    _description = "Danamon Bank Transfer Attachment"

    attachment_file = fields.Binary('Attachment File')
    file_name = fields.Char('File Name')