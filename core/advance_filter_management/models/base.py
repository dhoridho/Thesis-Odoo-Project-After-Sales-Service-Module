from odoo import fields, models, api, _
from lxml import etree
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval
from datetime import datetime
from odoo.addons.advanced_web_domain_widget.models.domain_prepare import prepare_domain_v2
from dateutil.relativedelta import relativedelta
import time

def context_today():
    return datetime.today()

class Base(models.AbstractModel):
    _inherit="base"

    def add_filter(self,res,custom_filters):
        arch = etree.fromstring(res)
        node = arch.xpath("//search/filter[last()]")
        uid = self.env.user.id
        if node:
            node[0].addnext(etree.Element("separator"))

            for custom_filter in custom_filters:    
                domain=[]
                dom = eval(custom_filter.domain) if custom_filter.domain else []
                
                if dom:
                    node = arch.xpath("//search/separator[last()]")

                    for dom_tuple in dom:    
                        if isinstance(dom_tuple, tuple)  or isinstance(dom_tuple, list) :
                            
                            field_name = dom_tuple[0]
                            operator_value = dom_tuple[1]
                            val = dom_tuple[2]
                        
                            left_value_split_list = field_name.split('.')
                            model_string = self._name
                            left_user = False
                            left_company = False
                            for field in left_value_split_list:
                                left_user = False
                                left_company = False
                                model_obj = self.env[model_string]
                                field_type = model_obj.fields_get()[field]['type']
                                if field_type in ['many2one', 'many2many', 'one2many']:
                                    field_relation = model_obj.fields_get()[field]['relation']
                                    model_string = field_relation
                                    if model_string == 'res.users':
                                        left_user = True
                                if left_user:
                                    if operator_value in ['in', 'not in']:
                                        if isinstance(val, list) and 0 in val:
                                            zero_index = val.index(0)
                                            val[zero_index] = self.env.user.id 
                                if left_company:
                                    if operator_value in ['in', 'not in']:
                                        if isinstance(val, list) and 0 in val:
                                            zero_index = val.index(0)
                                            val[zero_index] = self.env.company.id

                            if operator_value == 'date_filter':
                                domain+=prepare_domain_v2(dom_tuple)
                            else:
                                domain.append(dom_tuple)

                node = arch.xpath("//search/separator[last()]")
                if node:
                    elem = etree.Element(
                        "filter",
                        {
                            "name": "custom_filter_%s" % custom_filter.id,
                            "string": custom_filter.name,
                            "domain": str(domain),
                        },
                    )
                    node[0].addnext(elem)
        res = etree.tostring(arch)
        return res
    
    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        # pass
        new_arg=[]
        if args:
            for dom in args:
                if isinstance(dom, list) or isinstance(dom, tuple):
                    if dom[1] == 'date_filter':
                        new_arg += prepare_domain_v2(dom)
                    else:
                        new_arg.append(dom)
                else:
                    new_arg.append(dom)

        return super(Base, self)._search(new_arg, offset, limit, order, count=count, access_rights_uid=access_rights_uid)


    def add_groupby(self,res, custom_groupbys):
        arch = etree.fromstring(res)
        node = arch.xpath("//search/filter[last()]")
        if node:
            node[0].addnext(etree.Element("separator"))
            for custom_groupby in custom_groupbys:    
                node = arch.xpath("//search/separator[last()]")
                if node:
                    elem = etree.Element(
                        "filter",
                        {
                            "name": "custom_filter_%s" % custom_groupby.id,
                            "string": custom_groupby.name,
                            "context": str(
                                {"group_by": custom_groupby.fields_id.name}
                            ),
                        },
                    )
                    node[0].addnext(elem)
        res = etree.tostring(arch)
        return res

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    # def get_views(self, views, options=None):
        res = super().fields_view_get(view_id, view_type, toolbar, submenu)
        filters_obj=self.env["ir.filters"]
        if res['type']=='search':
            filter_ids = filters_obj.search(
                    [
                    ("model_id", "=", self._name),
                    ("user_ids", "in", self.env.user.id),
                    ("selection","=","filter")
                ]
            )
            groupby_ids=filters_obj.search(
                    [
                    ("model_id", "=", self._name),
                    ("user_ids", "in", self.env.user.id),
                    ("selection","=","group_by")
                ]
            )
            if filter_ids:
                for filter_id in filter_ids:
                    res['arch']=self.add_filter(res['arch'],filter_id)

            if groupby_ids:
                for grouby_id in groupby_ids:
                    # res['views']['search']=self.add_groupby(res['views'].get('search'),grouby_id)
                    res['arch']=self.add_groupby(res['arch'],grouby_id)
        
            # pass
        return res