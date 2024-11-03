from odoo import models, api, _
from odoo.exceptions import UserError


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    @api.constrains('identification_id', 'identification_no')
    def _check_identification_id(self):
        for emp in self:
            if emp.identification_id and emp.identification_no == '1':
                id_no = emp.identification_id
                if len(id_no) == 9 and id_no[1:-1] and id_no[1:-1].isdigit():
                    args = list(id_no[1:-1]) or []
                    count = 0
                    total_amount = 0
                    # Total Amount Calculation
                    for digit in args:
                        count = count + 1
                        if count == 1:
                            total_amount += int(digit) * 2
                        else:
                            total_amount += int(digit) * (9 - count)
                    # Checksum Calculation
                    if id_no[0:1].upper() in ('T', 'G'):
                        total_amount += 4
                    reminder = total_amount % 11
                    if id_no[0:1].upper() in ('S', 'T'):
                        rem_res = {0: 'J', 1: 'Z', 2: 'I', 3: 'H', 4:'G',
                                   5:'F', 6:'E', 7:'D', 8:'C', 9: 'B', 10:'A'}
                        if reminder and reminder in rem_res:
                            reminder = rem_res[reminder]
                    elif id_no[0:1].upper() in ('F', 'G'):
                        remdr_res = {0: 'X', 1: 'W', 2: 'U', 3: 'T', 4:'R',
                                   5:'Q', 6:'P', 7:'N', 8:'M', 9: 'L', 10:'K'}
                        if reminder and reminder in remdr_res:
                            reminder = remdr_res[reminder]
                    last_arg = id_no[-1].upper()
                    if last_arg != reminder:
                        raise UserError(_("Please enter valid NRIC Number."))
                else:
                    raise UserError(_("Please enter valid NRIC Number"))
