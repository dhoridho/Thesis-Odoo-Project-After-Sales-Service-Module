# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
import datetime
from odoo import fields, models, api
from datetime import date
from odoo.exceptions import ValidationError
from PyPDF2 import PdfFileWriter, PdfFileReader
from PyPDF2.generic import DictionaryObject, DecodedStreamObject, NameObject, createStringObject, ArrayObject
from odoo import models, fields, api, _
import io
import base64


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _post_pdf(self, save_in_attachment, pdf_content=None, res_ids=None):
        res = super(IrActionsReport, self)._post_pdf(save_in_attachment,
                                                     pdf_content=pdf_content,
                                                     res_ids=res_ids)
        # print("===============f> _post_pdf res_ids ", res_ids)
        # print("===============f> _post_pdf res ", res)
        # print("===============f> _post_pdf self.report_type ", self.report_type)
        # print("===============f> _post_pdf self.model ", self.model)
        # print("===============f> _post_pdf len(res_ids) ", len(res_ids))

        if self.report_type == 'qweb-pdf' and self.model == 'hr.applicant' and res_ids and len(res_ids) == 1:
            record = self.env[self.model].browse(res_ids)
            if record and record.file_cv and record.uploaded_cv_type == "application/pdf":
                writer = PdfFileWriter()
                pdf_content = [res]
                # print("================f> record.hr_merge_pdf_attachment_ids ", record.hr_merge_pdf_attachment_ids)
                datas = base64.b64decode(record.file_cv)
                # print("================f> datas ", datas)
                pdf_content.append(datas)
                for document in pdf_content:
                    reader = PdfFileReader(io.BytesIO(document), strict=False)
                    for page in range(0, reader.getNumPages()):
                        writer.addPage(reader.getPage(page))
                with io.BytesIO() as _buffer:
                    writer.write(_buffer)
                    merged_pdf = _buffer.getvalue()
                    _buffer.close()
                    # print("===============f> _post_pdf merged_pdf ", merged_pdf)
                    return merged_pdf
        return res