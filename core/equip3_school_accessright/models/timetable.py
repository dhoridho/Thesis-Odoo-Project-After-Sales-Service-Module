from odoo import models, fields, api, _
from odoo.osv import expression
from lxml import etree

class TimeTable(models.Model):
    _inherit = "time.table"

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        res = super(TimeTable, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        if  self.env.user.has_group('school.group_school_administration') or self.env.user.has_group('school.group_school_teacher'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
            
        return res

class TimeTableLine(models.Model):
    _inherit = 'time.table.line'

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        res = super(TimeTableLine, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        if  self.env.user.has_group('school.group_school_administration') or self.env.user.has_group('school.group_school_teacher'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
            
        return res
