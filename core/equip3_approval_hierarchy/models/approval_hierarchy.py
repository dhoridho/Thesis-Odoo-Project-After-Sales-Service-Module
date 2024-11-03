import base64
import requests
from odoo.http import request
from odoo.exceptions import ValidationError
import re

headers = {'content-type': 'application/json'}


class ApprovalHierarchy(object):
    def __init__(self,):
        pass


    def get_hierarchy(self, record, employee_manager, data, manager_ids, seq, level):
        if not employee_manager['parent_id']['user_id']:
            return manager_ids
        while data < int(level):
            manager_ids.append(employee_manager['parent_id']['user_id']['id'])
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_hierarchy(record, employee_manager['parent_id'], data, manager_ids, seq, level)
                break

        return manager_ids

        
        