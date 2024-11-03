from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, AccessError
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval
from odoo.http import request
from lxml import etree
from odoo.addons.simplify_access_management.models.models import BaseModel

# class BaseModel(models.AbstractModel):
#     _inherit = 'base'

@api.model
def _search(self, domain, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
    self._cr.execute(
        """SELECT value from ir_config_parameter where key='uninstall_simplify_access_management' """)
    value = self._cr.fetchone()
    if not value and self.env.user.id:
        try:
            self._cr.execute("SELECT id FROM ir_model WHERE model='" + self._name + "'")
            model_numeric_id = self._cr.fetchone()
            model_numeric_id = model_numeric_id and model_numeric_id[0] or False
            self._cr.execute("""
                            SELECT dm.id
                            FROM access_domain_ah as dm
                            WHERE dm.model_id=%s AND dm.apply_domain AND dm.access_management_id 
                            IN (SELECT am.id 
                                FROM access_management as am 
                                WHERE active='t' AND am.id 
                                IN (SELECT amusr.access_management_id
                                    FROM access_management_users_rel_ah as amusr
                                    WHERE amusr.user_id=%s))
                            """, [model_numeric_id, self.env.user.id])
        except:

            return super(BaseModel, self)._search(domain, offset=offset, limit=limit,
                                                    order=order, count=count, access_rights_uid=access_rights_uid)

        # access_domain_ah_ids = []
        access_domain_ah_ids = self.env['access.domain.ah'].browse(row[0] for row in self._cr.fetchall()).filtered(
            lambda line: self.env.company in line.access_management_id.company_ids and line.soft_restrict)
        for access_domain in access_domain_ah_ids:
            dom = safe_eval(access_domain.domain) if access_domain.domain else []
            dom = expression.normalize_domain(dom)
            if isinstance(dom, list):
                for tuple in dom:
                    if 'tuple' == type(tuple).__name__:
                        operator_value = tuple[1]
                        right_value = tuple[2]
                        if operator_value in ['in', 'not in']:
                            if isinstance(right_value, list) and 0 in right_value:
                                zero_index = right_value.index(0)
                                right_value[zero_index] = self.env.user.id
            domain += dom

    return super(BaseModel, self)._search(domain, offset=offset, limit=limit, order=order, count=count,
                                            access_rights_uid=access_rights_uid)

@api.model
def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    res = super(BaseModel, self).fields_view_get(view_id, view_type, toolbar, submenu)
    access_management_obj = self.env['access.management']
    cids = request.httprequest.cookies.get('cids') and request.httprequest.cookies.get('cids').split(',')[0] or request.env.company.id
    readonly_access_id = access_management_obj.search([('company_ids','in',int(cids)),('active','=',True),('user_ids','in',self.env.user.id),('readonly','=',True)])

    access_recs = self.env['access.domain.ah'].search([('access_management_id.company_ids','in',self.env.company.id),('access_management_id.user_ids','in',self.env.user.id),('access_management_id.active','=',True),('model_id.model','=',res['model'])])
    access_model_recs = self.env['remove.action'].search([('access_management_id.company_ids','in',self.env.company.id),('access_management_id.user_ids','in',self.env.user.id),('access_management_id.active','=',True),('model_id.model','=',res['model'])])

    if view_type == 'form':
        access_management_id = access_management_obj.search([('company_ids', 'in', self.env.company.id),
                                                                ('active', '=', True),
                                                                ('user_ids', 'in', self.env.user.id),
                                                                ('hide_chatter', '=', True)],
                                                            limit=1).id
        if access_management_id:
            doc = etree.XML(res['arch'])
            for div in doc.xpath("//div[@class='oe_chatter']"):
                div.getparent().remove(div)
            res['arch'] = etree.tostring(doc, encoding='unicode')
        else:
            if self.env['hide.chatter'].search([('access_management_id.company_ids', 'in', self.env.company.id),
                                                ('access_management_id.active', '=', True),
                                                ('access_management_id.user_ids', 'in', self.env.user.id),
                                                ('model_id.model', '=', self._name),
                                                ('hide_chatter', '=', True)],
                                                limit=1):

                doc = etree.XML(res['arch'])
                for div in doc.xpath("//div[@class='oe_chatter']"):
                    div.getparent().remove(div)
                res['arch'] = etree.tostring(doc, encoding='unicode')

    restrict_import = access_management_obj.search([('company_ids', 'in', self.env.company.id),
                                                    ('active', '=', True),
                                                    ('user_ids', 'in', self.env.user.id),
                                                    ('hide_import', '=', True)], limit=1).id

    if access_model_recs.filtered(lambda x: x.restrict_import) or restrict_import:
        if view_type in ['kanban', 'tree']:
            doc = etree.XML(res['arch'])
            doc.attrib.update({'import': 'false'})
            res['arch'] = etree.tostring(doc, encoding='unicode')

    if readonly_access_id:
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            doc.attrib.update({'create':'false', 'delete':'false','edit':'false'})

            res['arch'] = etree.tostring(doc, encoding='unicode')
        if view_type == 'tree':
            doc = etree.XML(res['arch'])
            doc.attrib.update({'create':'false', 'delete':'false','edit':'false'})

            res['arch'] = etree.tostring(doc, encoding='unicode')

        if view_type == 'kanban':
            doc = etree.XML(res['arch'])
            doc.attrib.update({'create':'false', 'delete':'false','edit':'false'})

            res['arch'] = etree.tostring(doc, encoding='unicode').replace('&amp;quot;','&quot;')

    else:
        
        if access_model_recs:
            delete = 'true'
            edit = 'true'
            create = 'true'
            for access_model in access_model_recs:

                if access_model_recs.view_ids:
                    for view in access_model_recs.view_ids:
                        if view.type == view_type:
                            if access_model.restrict_create:
                                create = 'false'
                            if access_model.restrict_edit:
                                edit = 'false'
                            if access_model.restrict_delete:
                                delete = 'false'
                            doc = etree.XML(res['arch'])
                            doc.attrib.update({'create':create, 'delete':delete,'edit':edit})
                            res['arch'] = etree.tostring(doc, encoding='unicode')
                            # arch.attrib.update({'create': create, 'delete': delete, 'edit': edit})
                else :
                    if access_model.restrict_create:
                        create = 'false'
                    if access_model.restrict_edit:
                        edit = 'false'
                    if access_model.restrict_delete:
                        delete = 'false'
                    
                    if view_type == 'form':
                        doc = etree.XML(res['arch'])
                        doc.attrib.update({'create':create, 'delete':delete,'edit':edit})

                        res['arch'] = etree.tostring(doc, encoding='unicode')
                    if view_type == 'tree':
                        doc = etree.XML(res['arch'])
                        doc.attrib.update({'create':create, 'delete':delete,'edit':edit})

                        res['arch'] = etree.tostring(doc, encoding='unicode')

                    if view_type == 'kanban':
                        doc = etree.XML(res['arch'])
                        doc.attrib.update({'create':create, 'delete':delete,'edit':edit})

                        res['arch'] = etree.tostring(doc, encoding='unicode')
                
        if access_recs:
            delete = 'false'
            edit = 'false'
            create = 'false'
            for access_rec in access_recs:
                if access_rec.create_right:
                    create = 'true'
                if access_rec.write_right:
                    edit = 'true'
                if access_rec.delete_right:
                    delete = 'true'

            if view_type == 'form':
                doc = etree.XML(res['arch'])
                doc.attrib.update({'create':create, 'delete':delete,'edit':edit})

                res['arch'] = etree.tostring(doc, encoding='unicode')
            if view_type == 'tree':
                doc = etree.XML(res['arch'])
                doc.attrib.update({'create':create, 'delete':delete,'edit':edit})

                res['arch'] = etree.tostring(doc, encoding='unicode')

            if view_type == 'kanban':
                doc = etree.XML(res['arch'])
                doc.attrib.update({'create':create, 'delete':delete,'edit':edit})

                res['arch'] = etree.tostring(doc, encoding='unicode').replace('&amp;quot;','&quot;')
    return res
    
BaseModel.fields_view_get = fields_view_get