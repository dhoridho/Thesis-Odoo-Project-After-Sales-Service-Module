# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
import logging
from collections import defaultdict

from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.exceptions import ValidationError, RedirectWarning, UserError
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    def _get_tax_code_selection(self):
        res = ['%s-%s-%s'%('22','100',len(str(x)) == 1 and '0'+str(x) or str(x)) for x in list(range(6,25))]
        res += ['%s-%s-%s'%('22','401',len(str(x)) == 1 and '0'+str(x) or str(x)) for x in list(range(1,4))]
        res += ['%s-%s-%s'%('22','403',len(str(x)) == 1 and '0'+str(x) or str(x)) for x in list(range(1,3))]
        res += ['%s-%s-%s'%('22','404','01')]
        res += ['%s-%s-%s'%('22','900','01')]
        res += ['%s-%s-%s'%('23','100',len(str(x)) == 1 and '0'+str(x) or str(x)) for x in list(range(1,6))]
        res += ['%s-%s-%s'%('24','100',len(str(x)) == 1 and '0'+str(x) or str(x)) for x in list(range(1,3))]
        res += ['%s-%s-%s'%('24',i,'01') for i in [101,102,103]]        
        res += ['%s-%s-%s'%('24','104',len(str(x)) == 1 and '0'+str(x) or str(x)) for x in list(range(1,70))]
        res += ['%s-%s-%s'%('27','100',len(str(x)) == 1 and '0'+str(x) or str(x)) for x in list(range(1,7))]
        res += ['%s-%s-%s'%('27','102',len(str(x)) == 1 and '0'+str(x) or str(x)) for x in list(range(1,3))]
        res += ['%s-%s-%s'%('27',i,'01') for i in [101,103,104,105]]
        res += ['%s-%s-%s'%('28','401','03')]
        res += ['%s-%s-%s'%('28','402',len(str(x)) == 1 and '0'+str(x) or str(x)) for x in list(range(1,4))]
        res += ['%s-%s-%s'%('28','403',len(str(x)) == 1 and '0'+str(x) or str(x)) for x in list(range(1,3))]
        res += ['%s-%s-%s'%('28','405',len(str(x)) == 1 and '0'+str(x) or str(x)) for x in list(range(1,3))]
        res += ['%s-%s-%s'%('28','409',len(str(x)) == 1 and '0'+str(x) or str(x)) for x in list(range(1,15))]
        for i in [410,411,417,499]:
            res += ['%s-%s-%s'%('28',i,len(str(x)) == 1 and '0'+str(x) or str(x)) for x in list(range(1,3))]
        for i in [413,419,423]:
            res += ['%s-%s-%s'%('28',i,'01')]
        res += ['%s-%s-%s'%('28','421',len(str(x)) == 1 and '0'+str(x) or str(x)) for x in list(range(1,6))]
        res += ['%s-%s-%s'%('29','101','01')]
        res.sort()
        result = [(x,x) for x in res]
        return result
    
    def _get_doc_code_selection(self):
        result = [('%s'%('0'+str(x) or str(x)),'%s'%('0'+str(x) or str(x))) for x in list(range(1,9))]
        return result
    
    tax_code = fields.Selection(selection=_get_tax_code_selection, string='Kode Objek Pajak')
    doc_code = fields.Selection(selection=_get_doc_code_selection, string='Jenis Dokumen')