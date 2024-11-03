
import base64
import tempfile

from datetime import datetime

from odoo import _, fields, models
from odoo import tools
from odoo.exceptions import ValidationError

from xlrd import open_workbook


def _offset_format_timestamp(src_tstamp_str, src_format, dst_format,
                             ignore_unparsable_time=True, context=None):
    """Offset format timestamp.

    Convert a source timestamp string into a destination timestamp string,
    attempting to apply the
    correct offset if both the server and local timezone are recognized, or no
    offset at all if they aren't or if tz_offset is false (i.e. assuming they
    are both in the same TZ).

    @param src_tstamp_str: the str value containing the timestamp.
    @param src_format: the format to use when parsing the local timestamp.
    @param dst_format: the format to use when formatting the resulting
                       timestamp.
    @param server_to_client: specify timezone offset direction
                             (server=src and client=dest if True,
                             or client=src and server=dest if False)
    @param ignore_unparsable_time: if True, return False if src_tstamp_str
                                   cannot be parsed
                                   using src_format or formatted
                                   using dst_format.

    @return: destination formatted timestamp, expressed in the destination
             timezone if possible
             and if tz_offset is true, or src_tstamp_str if timezone offset
             could not be determined.
    """
    if not src_tstamp_str:
        return False

    res = src_tstamp_str
    if src_format and dst_format:
        try:
            #  dt_value needs to be a datetime.datetime object
            #  (so no time.struct_time or mx.DateTime.DateTime here!)
            dt_value = datetime.strptime(src_tstamp_str, src_format)
            if context.get('tz', False):
                try:
                    import pytz
                    src_tz = pytz.timezone('UTC')
                    dst_tz = pytz.timezone(context['tz'])
                    src_dt = src_tz.localize(dt_value, is_dst=True)
                    dt_value = src_dt.astimezone(dst_tz)
                except:
                    pass
            res = dt_value.strftime(dst_format)
        except:
            #  Normal ways to end up here are if strptime or strftime failed
            if not ignore_unparsable_time:
                return False
            pass
    return res


class UploadXlsWiz(models.TransientModel):

    _name = "upload.xls.wiz"
    _description = "Upload Xls Wizard"

    _description = 'Upload xls file for allowances or deductions input fields.'

    in_file = fields.Binary('Input File', required=True)
    datas_fname = fields.Char('Filename')
    date_start = fields.Date('Start Date ')
    date_stop = fields.Date('End Date')
    clear_all_prev_value = fields.Boolean('OVERWRITE ALL VALUES',
                                          default=True)

    def upload_file(self):
        """Upload the xls file.

        @param self : Current Record Set
        ------------------------------------------------------
        """
        temp_path = tempfile.gettempdir()
        user_object = self.env['res.users']
        payslip_object = self.env['hr.payslip']
        employee_object = self.env['hr.employee']
        for upload_rec in self:
            filename_str = str(upload_rec.datas_fname)
            #  split_file = filename_str.split('.')
            if not filename_str[-4:] == ".xls":
                raise ValidationError(_('Select .xls file only'))
            csv_data = base64.decodestring(upload_rec.in_file)
            fp = open(temp_path + '/xsl_file.xls', 'wb+')
            fp.write(csv_data)
            fp.close()
            wb = open_workbook(temp_path + '/xsl_file.xls')
            hr_rule_input_list = []
            context = self.env.context
            context = dict(context)
            for input in self.env['hr.rule.input'].search([]):
                hr_rule_input_list.append(input.code)
            xls_dict = {}
            xls_new_dict = {}
            for sheet in wb.sheets():
                for rownum in range(sheet.nrows):
                    if rownum == 0:
                        i = 1
                        first_headers = []
                        header_list = sheet.row_values(rownum)
                        new_header_list = sheet.row_values(rownum)
                        for header in new_header_list:
                            if header not in hr_rule_input_list and header \
                                    not in ['name', 'NAME', 'REMARKS',
                                            'EMPLOYEELOGIN']:
                                raise ValidationError(_(
                                    'Error \n Check '
                                    'Salary input code. %s Salary Input '
                                    'code not exists.' % header))
                        for header in header_list:
                            xls_dict.update({i: tools.ustr(header)})
                            i += 1
                            if header in first_headers:
                                raise ValidationError(_(
                                    'Error \n Duplicate '
                                    'salary input code %s found.' % header))
                            elif header not in ['name', 'NAME']:
                                first_headers.append(header)
                        remark_index = header_list.index('REMARKS')
                    else:
                        i = 1
                        headers = sheet.row_values(rownum)
                        for record in headers:
                            xls_new_dict.update({i: tools.ustr(record)})
                            i += 1
                        emp_login = ''
                        x = sheet.row_values(rownum)[header_list.index(
                                                     'EMPLOYEELOGIN')]
                        if isinstance(x, float):
                            emp_login = tools.ustr(int(
                                sheet.row_values(rownum)[header_list.index(
                                                         'EMPLOYEELOGIN')]))
                        else:
                            emp_login = tools.ustr(
                                sheet.row_values(rownum)[header_list.index(
                                                         'EMPLOYEELOGIN')])
                        user_ids = user_object.search([('login', '=',
                                                        emp_login)])
                        if not user_ids:
                            user_ids = user_object.search([('login', '=',
                                                            emp_login),
                                                           ('active', '=',
                                                            False)])
                            if user_ids:
                                raise ValidationError(_(
                                    'Error \n Employee '
                                    'login %s is inactive for row number '
                                    '%s. ' % (emp_login, rownum + 1)))
                            raise ValidationError(_(
                                'Error \n Employee login '
                                '%s not found for row number '
                                '%s. ' % (emp_login, rownum + 1)))
                        user_ids = user_ids.ids
                        emp_ids = employee_object.search([('user_id', 'in',
                                                           user_ids)])
                        if not emp_ids:
                            domain = [('user_id', 'in', user_ids),
                                      ('active', '=', False)]
                            emp_ids = employee_object.search(domain)
                            if emp_ids:
                                raise ValidationError(_(
                                    'Error \n Employee is '
                                    'inactive for login %s for row number '
                                    '%s. ' % (emp_login, rownum + 1)))
                            raise ValidationError(_(
                                'Error \n No employee '
                                'found for %s login name for row number '
                                '%s.' % (emp_login, rownum + 1)))
                        employe_ids = emp_ids.ids
                        if employe_ids:
                            contract_obj = self.env['hr.contract']
                            domain = [('employee_id', '=', employe_ids[0]),
                                      ('date_start', '<=',
                                       upload_rec.date_stop), '|',
                                      ('date_end', '>=', upload_rec.date_stop),
                                      ('date_end', '=', False)]
                            contract_ids = contract_obj.search(domain)
                            if not contract_ids:
                                raise ValidationError(_(
                                    'Error \n Contract '
                                    'not found for Employee login %s in row '
                                    'number %s.' % (emp_login, rownum + 1)))
                            p_domain = [('employee_id', '=', employe_ids[0]),
                                        ('date_from', '>=',
                                         upload_rec.date_start),
                                        ('date_to', '<=',
                                         upload_rec.date_stop),
                                        ('state', 'in', ['draft', 'done',
                                                         'verify'])]
                            pay_slip_ids = payslip_object.search(p_domain)
                            if not pay_slip_ids.ids:
                                raise ValidationError(_(
                                    'Error \n Payslip not '
                                    'found for Employee login %s in row '
                                    'number %s.' % (emp_login, rownum + 1)))
                            for pay_slip in pay_slip_ids:
                                if not pay_slip.contract_id:
                                    raise ValidationError(_(
                                        'Error \n '
                                        'Employee contract not found or '
                                        'not assign in payslip for %s '
                                        'for row number '
                                        '%s.' % (pay_slip.employee_id.name,
                                                 rownum + 1)))
                                note = pay_slip.note or ''
                                user_data = self.env.user
                                context.update({'tz': user_data.tz})
                                date = datetime.today()
                                format1 = '%Y-%m-%d %H:%M:%S'
                                format2 = '%d-%B-%Y %H:%M:%S'
                                user_current_date = _offset_format_timestamp(
                                    date, format1, format2, context=context)
                                note += '\nUploaded by ' + \
                                    tools.ustr(user_data.name or '') + \
                                    ' on ' + \
                                    tools.ustr(
                                        user_current_date.strftime(
                                            '%d-%b-%Y %H:%M:%S')) + \
                                    ' \n ---------------------------\
                                    --------------------------- \n'
                                for xls in xls_dict:
                                    for input_data in pay_slip.input_line_ids:
                                        xls_dict[xls]
                                        if input_data.code == xls_dict[xls]:
                                            salary_amt = 0.00
                                            salary_amt = xls_new_dict.get(
                                                xls).strip()
                                            if salary_amt:
                                                salary_amt = float(salary_amt)
                                            else:
                                                salary_amt = 0.00
                                            if upload_rec.clear_all_prev_value:
                                                input_line_amount = salary_amt\
                                                    or 0.00
                                            else:
                                                input_line_amount = salary_amt\
                                                    + input_data.amount or 0.0
                                            input_data.write({
                                                'amount': input_line_amount})
                                            note += tools.ustr(xls_dict[xls]) \
                                                + " " * 5 + tools.ustr(
                                                    salary_amt) + " " * 5 + \
                                                tools.ustr(sheet.row_values(
                                                    rownum)[remark_index]) + \
                                                '\n'
                                if note:
                                    pay_slip.write({'note': note})
                                    pay_slip.compute_sheet()
        return {'type': 'ir.actions.client', 'tag': 'reload'}
