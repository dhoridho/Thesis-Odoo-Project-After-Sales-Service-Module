# Copyright 2020 Creu Blanca
# Copyright 2020 Ecosoft Co., Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
from io import BytesIO

from odoo import _, fields, models, api
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)
try:
    from PyPDF2 import PdfFileReader, PdfFileWriter
except ImportError as err:
    _logger.debug(err)


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    # encrypt = fields.Selection(
    #     [("manual", "Manual Input Password"), ("auto", "Auto Generated Password")],
    #     string="Encryption",
    #     help="* Manual Input Password: allow user to key in password on the fly. "
    #          "This option available only on document print action.\n"
    #          "* Auto Generated Password: system will auto encrypt password when PDF "
    #          "created, based on provided python syntax.",
    # )
    # encrypt_password = fields.Char(
    #     help="Python code syntax to gnerate password.",
    # )
    encrypt = fields.Boolean(
        string="Encryption",
        help="Enable/disable encryption report file.",
    )
    encrypt_type = fields.Selection(
        [("manual", "Manual Input Password"), ("auto", "Auto Generated Password")],
        string="Encryption Type",
        help="* Manual Input Password: allow user to key in password manual.\n"
             "* Auto Generated Password: system will auto encrypt password when Report "
             "created, based on fields.",
    )
    manual_password = fields.Char(help="Input manual password.")
    password_fields = fields.Many2one('ir.model.fields', string='Password Fields',
                                   domain="[('model','=',model),('name','!=','id'),('name','!=','sequence'),"
                                          "('store','=',True),'|',"
                                          "('ttype','=','many2one'),('ttype','=','char')]")
    password_sub_field = fields.Many2one('ir.model.fields', string='Password Sub Field')

    @api.onchange("encrypt")
    def _onchange_encrypt(self):
        if self.encrypt:
            self.manual_password = False
            self.password_fields = False
            self.password_sub_field = False
        else:
            self.manual_password = False
            self.password_fields = False
            self.password_sub_field = False

    @api.onchange("encrypt_type")
    def _onchange_encrypt_type(self):
        if self.encrypt_type:
            self.manual_password = False
            self.password_fields = False
            self.password_sub_field = False
        else:
            self.manual_password = False
            self.password_fields = False
            self.password_sub_field = False

    @api.onchange("password_fields")
    def _onchange_password_fields(self):
        domain_dict = {'domain': {'password_sub_field': [('id', '=', -1)]}}
        if self.password_fields and self.password_fields.relation:
            self.password_sub_field = False
            domain_dict = {'domain': {'password_sub_field': [('model','=',self.password_fields.relation),('name','!=','id'),('name','!=','sequence'),('store','=',True),('ttype','=','char')]}}
        elif self.password_fields and not self.password_fields.relation:
            self.password_sub_field = False
            domain_dict = domain_dict
        return domain_dict

    def _render_qweb_pdf(self, res_ids=None, data=None):
        document, ttype = super(IrActionsReport, self)._render_qweb_pdf(
            res_ids=res_ids, data=data
        )
        if isinstance(res_ids, list):
            password = self._get_pdf_password(res_ids[:1]) if res_ids else False
        else:
            password = self._get_pdf_password([res_ids][:1]) if res_ids else False
        document = self._encrypt_pdf(document, password)
        return document, ttype

    # def _get_pdf_password(self, res_id):
    #     encrypt_password = False
    #     if self.encrypt == "manual":
    #         # If use document print action, report_download() is called,
    #         # but that can't pass context (encrypt_password) here.
    #         # As such, file will be encrypted by report_download() again.
    #         # --
    #         # Following is used just in case when context is passed in.
    #         encrypt_password = self._context.get("encrypt_password", False)
    #     elif self.encrypt == "auto" and self.encrypt_password:
    #         obj = self.env[self.model].browse(res_id)
    #         try:
    #             encrypt_password = safe_eval(self.encrypt_password, {"object": obj})
    #         except Exception:
    #             raise ValidationError(
    #                 _("Python code used for encryption password is invalid.\n%s")
    #                 % self.encrypt_password
    #             )
    #     return encrypt_password

    def _get_pdf_password(self, res_id):
        encrypt_password = False
        if self.encrypt:
            if self.encrypt_type == "manual" and self.manual_password:
                encrypt_password = self.manual_password
            elif self.encrypt_type == "auto":
                obj = self.env[self.model].browse(res_id)
                if self.password_fields and not self.password_sub_field:
                    if self.password_fields.relation:
                        raise ValidationError(_("Password fields used for encryption password is invalid"))
                    else:
                        field_name = self.password_fields.name
                        field_password = str('object.') + str(field_name)
                        try:
                            encrypt_password = safe_eval(field_password, {"object": obj})
                        except Exception:
                            raise ValidationError(
                                _("Password field used for encryption password is invalid.\n%s")
                                % field_name
                            )
                elif self.password_fields and self.password_sub_field:
                    fields = self.password_fields.name
                    field_name = str('object.') + str(fields)
                    res_id = safe_eval(field_name, {"object": obj})
                    model_sub = self.password_fields.relation
                    obj_sub = self.env[model_sub].browse(res_id.id)
                    field_sub = self.password_sub_field.name
                    field_password = str('object.') + str(field_sub)
                    try:
                        encrypt_password = safe_eval(field_password, {"object": obj_sub})
                    except Exception:
                        raise ValidationError(
                            _("Password sub field used for encryption password is invalid.\n%s")
                            % field_sub
                        )
        return encrypt_password

    def _encrypt_pdf(self, data, password):
        if not password:
            return data
        output_pdf = PdfFileWriter()
        in_buff = BytesIO(data)
        pdf = PdfFileReader(in_buff)
        output_pdf.appendPagesFromReader(pdf)
        output_pdf.encrypt(password)
        buff = BytesIO()
        output_pdf.write(buff)
        return buff.getvalue()

    # def _get_readable_fields(self):
    #     return super()._get_readable_fields() | {"encrypt"}

    def _get_readable_fields(self):
        return super()._get_readable_fields() | {"encrypt", "encrypt_type"}
