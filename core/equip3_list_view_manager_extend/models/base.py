from odoo import models, api, fields, _
from datetime import datetime
import pytz

class Base(models.AbstractModel):
    """ The base model, which is implicitly inherited by all models. """
    _inherit = 'base'


    @api.model
    def search(self, args=[], offset=0, limit=None, order=None, count=False):
        default_count = count
        domain = args
        if self._context.get('from_ks_list_view_manager') and self._context.get('default_fields'):
            if domain and type(domain)==list:
                field_obj = self.env['ir.model.fields']
                user_tz = self.env.user.tz or pytz.utc
                count = 0
                for dom in domain:
                    if dom and type(dom) in [list,tuple] and dom[0] not in ['|', '&'] and len(dom) == 3:
                        field_name = dom[0]
                        operator_field = dom[1]
                        value_field = dom[2]
                        if operator_field == '=':
                            operator_field = '=='
                        field_rec = field_obj.sudo().with_context(from_ks_list_view_manager=0).search_read([('name','=',field_name),('model_id.model','=',self._name)],limit=1,fields=['store','ttype'])
                        if field_rec and not field_rec[0]['store'] and value_field and (isinstance(value_field, str) or isinstance(value_field, int) or isinstance(value_field, float)):
                            rec_all = self.with_context(from_ks_list_view_manager=0).search_read(domain=[('id','!=',False)],fields=[field_name])
                            rec_ids = []
                            need_change_domain = False
                            for rec in rec_all:
                                value_field = dom[2]
                                operations = {
                                        '==': lambda x, y: x == y,
                                        '!=': lambda x, y: x != y,
                                        '<': lambda x, y: x < y,
                                        '<=': lambda x, y: x <= y,
                                        '>': lambda x, y: x > y,
                                        '>=': lambda x, y: x >= y,
                                        'in': lambda x, y: x in y
                                    }
                                value_check = False

                                if rec[field_name]:
                                    if field_rec[0]['ttype'] == 'date':
                                        if isinstance(value_field, str) and 'Z' in value_field:
                                            need_change_domain = True
                                            if rec[field_name]:
                                                value_field = datetime.strptime(value_field, "%Y-%m-%dT%H:%M:%S.%fZ")
                                                value_field = value_field.date()
                                                value_check = operations[operator_field](rec[field_name], value_field)

                                    elif field_rec[0]['ttype'] == 'datetime':
                                        if isinstance(value_field, str) and 'Z' in value_field:
                                            need_change_domain = True
                                            if rec[field_name]:
                                                local = pytz.timezone(user_tz)
                                                value_field = datetime.strptime(value_field, "%Y-%m-%dT%H:%M:%S.%fZ")
                                                value_field = datetime.strftime(local.localize(value_field).astimezone(pytz.utc),"%Y-%m-%d %H:%M:%S")
                                                value_field =  datetime.strptime(value_field, "%Y-%m-%d %H:%M:%S")
                                                rec[field_name] = datetime.strftime(rec[field_name],"%Y-%m-%d %H:%M:%S")
                                                rec[field_name] = datetime.strptime(rec[field_name],"%Y-%m-%d %H:%M:%S")
                                                value_check = operations[operator_field](rec[field_name], value_field)

                                    elif field_rec[0]['ttype'] == 'many2one' and isinstance(value_field, str):
                                        need_change_domain = True
                                        if rec[field_name] and value_field:
                                            value_check = value_field.lower() in rec[field_name][1].lower()

                                    elif field_rec[0]['ttype'] in ['char','text','html'] and isinstance(value_field, str):
                                        need_change_domain = True
                                        if rec[field_name] and value_field:
                                            value_check = value_field.lower() in rec[field_name].lower()


                                    elif field_rec[0]['ttype'] == 'selection' and isinstance(value_field, str):
                                        need_change_domain = True
                                        if rec[field_name] and value_field:
                                            value_check = (value_field == rec[field_name])

                                    elif field_rec[0]['ttype'] in ['integer','float','monetary']:
                                        try:
                                            value_field = float(value_field)
                                            need_change_domain = True
                                            value_check = (value_field == rec[field_name])
                                        except:
                                            break


                                
                                if rec[field_name] and value_check:
                                    rec_ids.append(rec['id'])
                                if  not value_check and rec['id'] in rec_ids:
                                    rec_ids.remove(rec['id'])

                            if need_change_domain:
                                domain[count] = ('id', 'in', rec_ids)
                    count+=1
                args = domain
        return super(Base, self).search(args, offset, limit, order, default_count)