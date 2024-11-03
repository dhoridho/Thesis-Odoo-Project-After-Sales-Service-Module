from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError
from datetime import datetime, date
from datetime import timedelta


class confirm_wizard(models.TransientModel):
    _name = 'task.confirm.wizard.const'
    _description = "Task Confirm Wizard"

    result = fields.Html()
    @api.model
    def default_get(self,fields):
        res=super(confirm_wizard,self).default_get(fields)
        if self._context.get('active_id'):
            current_tast_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            project_task_id = self.env['project.task'].browse(self._context.get('active_id'))

            result ="""
            <h2>The current date is not match with predecessor date and the lag days,<br/>
            check below and more </h2>
            <h2>current date: """+str(current_tast_date)+"""</h2>
            <table width="100%" cellspacing="1" cellpadding="4" border="1" height="73">
                        <tbody>
                            <tr style="font-weight:bold;">
                                <th>&nbsp;Task&nbsp;</th>
                                <th>&nbsp;Actualdate&nbsp;&nbsp;  +</th>
                                <th>&nbsp;lag &nbsp;&nbsp; = </th>
                                <th>&nbsp;Final actual date &nbsp;</th>
                            </tr>
                        """

            count = 0
            
            for val in project_task_id.predecessor_ids:
                
                if val.parent_task_id.actual_start_date:
                    
                    if count <= 5:
                        count += 1
                        current_tast_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        parent_date_1 = datetime.strptime(val.parent_task_id.actual_start_date, "%Y-%m-%d %H:%M:%S").strftime('%Y-%m-%d %H:%M:%S')
                        parent_date_2 = datetime.strptime(parent_date_1, "%Y-%m-%d %H:%M:%S")
                        
                        lag_days = val.lag_qty
                        final_days = parent_date_2
                        if val.lag_type == 'day':
                            final_days = parent_date_2 + timedelta(days=lag_days)
                        if val.lag_type == 'hour':
                            final_days = parent_date_2 + timedelta(hours=lag_days)
                        if val.lag_type == 'minute':
                            final_days = parent_date_2 + timedelta(minutes=lag_days)
                        f_days = final_days.strftime('%Y-%m-%d %H:%M:%S')
                        if f_days > current_tast_date:

                            result += (""" <tr>
                                            <td>&nbsp;%s&nbsp;</td>
                                            <td>&nbsp;%s&nbsp;</td>
                                            <td>&nbsp;%s(%s)&nbsp;</td>
                                            <td>&nbsp;%s&nbsp;</td>
                                           </tr>
                                        """) % (val.parent_task_id.name, parent_date_2,lag_days,val.lag_type,f_days)
            result += """</tbody>
                                            </table><br/>
                        <h2>Are you still want to start the task?</h2>"""
        res.update({'result':result})
        return res

    def yes_confirm(self):
        if self._context.get('active_id'):
            project_task_id = self.env['project.task'].browse(self._context.get('active_id'))
            project_task_id.state = 'inprogress'

    def no(self):
        return False
