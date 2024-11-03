from datetime import datetime
from numpy import mat, timedelta64
from odoo.http import request
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval, time
from pytz import timezone




class approvalMatrixUser(object):
    def __init__(self,obj):
        self.obj = obj
        
    def get_approval_user(self):
        if self.obj.approval_matrix_ids:
            sequence = [data.sequence for data in self.obj.approval_matrix_ids.filtered(lambda line:  len(line.approver_confirm.ids) != line.minimum_approver )]
            if sequence:
                minimum_sequence = min(sequence)
                approve_user= self.obj.approval_matrix_ids.filtered(lambda line: request.env.user.id in line.approver_id.ids and request.env.user.id not in  line.approver_confirm.ids and line.sequence == minimum_sequence)
                if approve_user:
                    self.obj.user_approval_ids = [(6,0,[request.env.user.id])]
                else:
                    self.obj.user_approval_ids = False
            else:
                self.obj.user_approval_ids = False
        else:
            self.obj.user_approval_ids = False
        
        

class approvalMatrix(object):
    def __init__(self,model,obj,setting_params,level_param):
        self.model = model
        self.obj = obj
        self.apply_to = {}
        self.setting_params = setting_params
        self.level_param = level_param
        
    def set_apply_to(self,apply_to):
        self.apply_to['data']=apply_to
        
        
    def get_approval_user(self):
        pass
        

    def get_approval_matrix(self,is_approver_by_type=False):
        setting = request.env['ir.config_parameter'].sudo().get_param(self.setting_params)
        if setting == 'employee_hierarchy':
            self.obj.approval_matrix_ids = self.approval_by_hierarchy(self.obj)
        else:
            if not is_approver_by_type:
                for data in self.apply_to['data']:
                    approval_matrix = request.env[self.model].search(safe_eval(data['apply_to']),order=safe_eval(data['order']),limit=data['limit'])
                    matrix = approval_matrix.filtered(safe_eval(data['filter'],{'record':self.obj}))
                    if matrix:
                        data_approvers = []
                        for line in matrix.approval_matrix_ids:
                            data_approvers.append((0,0,{'sequence':line.sequence,'minimum_approver':line.minimum_approver,'approver_id':[(6,0,line.approvers.ids)]}))
                        self.obj.approval_matrix_ids = data_approvers
                        break;
            else:
                for data in self.apply_to['data']:
                    approval_matrix = request.env[self.model].search(safe_eval(data['apply_to']),order=safe_eval(data['order']),limit=data['limit'])
                    matrix = approval_matrix.filtered(safe_eval(data['filter'],{'record':self.obj}))
                    if matrix:
                        data_approvers = []
                        for line in matrix.approval_matrix_ids:
                            if line.approver_type == 'specific_approver':
                                data_approvers.append((0,0,{'sequence':line.sequence,'minimum_approver':line.minimum_approver,'approver_id':[(6,0,line.approvers.ids)]}))
                            else:
                                data_approvers.append((0,0,{'sequence':line.sequence,'minimum_approver':line.minimum_approver,'approver_id':[(6,0,self.get_approval_type_by_hierarchy(self.obj))]}))
                        self.obj.approval_matrix_ids = data_approvers
                        break;
                
                
    def get_approval_type_by_hierarchy(self,record):
        approval_ids = []
        seq = 1
        data = 0
        line = self.get_manager_approval_type(record.employee_id,data,approval_ids,seq)
        return line
    
    def get_manager_approval_type(self,employee_manager,data,approval_ids,seq):
        try:
            if not employee_manager['parent_id']['user_id']:
                    return approval_ids
            while employee_manager:
                approval_ids.append(employee_manager['parent_id']['user_id']['id'])
                data += 1
                seq +=1
                if employee_manager['parent_id']['user_id']['id']:
                    self.get_manager_approval_type(employee_manager['parent_id'],data,approval_ids,seq)
                    break
            
            return approval_ids
        except RecursionError:
            pass
    
    def approval_by_hierarchy(self,record):
        approval_ids = []
        seq = 1
        data = 0
        line = self.get_manager(record,record.employee_id,data,approval_ids,seq)
        return line
        
        
    
    
    def get_manager(self,record,employee_manager,data,approval_ids,seq):
        setting_level = request.env['ir.config_parameter'].sudo().get_param(self.level_param)
        if not setting_level:
            raise ValidationError("level not set")
        if not employee_manager['parent_id']['user_id']:
                return approval_ids
        while data < int(setting_level):
            approval_ids.append( (0,0,{'sequence':seq,'approver_id':[(4,employee_manager['parent_id']['user_id']['id'])]}))
            data += 1
            seq +=1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager(record,employee_manager['parent_id'],data,approval_ids,seq)
                break
        
        return approval_ids



class approvalMatrixWizard(object):
    def __init__(self,obj,sequence,sequence_apply,approval):
        self.obj = obj
        self.sequence = sequence
        self.sequence_apply = sequence_apply
        self.approval = approval

    def submit(self,obj_state,state_obj_approve,state_obj_reject):
        if not self.obj.feedback:
            self.obj.feedback = ""
        sequence = [data.sequence for data in safe_eval(self.sequence,{'record':self.obj})]
        sequence_apply = [data.sequence for data in safe_eval(self.sequence_apply,{'record':self.obj})]
        max_seq =  max(sequence)
        min_seq =  min(sequence_apply)
        now = datetime.now(timezone(request.env.user.tz))
        dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"
        approval = safe_eval(self.approval,{'record':self.obj,'min_seq':min_seq})
        if approval:
            approval.approver_confirm = [(4,request.env.user.id)]
            if not approval.approval_status:
                approval.approval_status = f"{request.env.user.name}:Approved" if  self.obj.state == "approved" else f"{request.env.user.name}:Rejected"
                if self.obj.feedback:
                    approval.feedback = f"{request.env.user.name}:{self.obj.feedback}"
                else:
                    approval.feedback = ""
            else:
                string_approval = []
                string_approval.append(approval.approval_status)
                if  self.obj.state == "approved":
                    string_approval.append(f"{request.env.user.name}:Approved")
                    approval.approval_status = "\n".join(string_approval)
                else:
                    string_approval.append(f"{request.env.user.name}:Rejected")
                    approval.approval_status = "\n".join(string_approval)
                if self.obj.feedback:
                    feedback_list = [approval.feedback,
                                     f"{request.env.user.name}:{self.obj.feedback}"]
                    final_feedback = "\n".join(feedback_list)
                    approval.feedback = f"{final_feedback}"
                elif approval.feedback and not self.obj.feedback:
                    approval.feedback = approval.feedback
                else:
                    approval.feedback = ""
            timestamp = f"{request.env.user.name}:{dateformat}"
            if approval.timestamp:
                string_timestammp = [approval.timestamp]
                string_timestammp.append(timestamp)
                approval.timestamp= "\n".join(string_timestammp)
            if not approval.timestamp:
                approval.timestamp =  timestamp
            if self.obj.state == "rejected":
                obj_state.write(state_obj_reject)  
                return False
            if len(approval.approver_confirm) == approval.minimum_approver and approval.sequence == max_seq and self.obj.state == "approved":
                obj_state.write(state_obj_approve) 
                return True

            
        if not approval:
            raise ValidationError("You not approval for this Request")        
  
    
    
    
        