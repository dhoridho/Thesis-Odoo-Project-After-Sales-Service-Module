'''
Created on Nov 18, 2018

@author: Zuhair Hammadi
'''
from odoo.addons.web.controllers.main import Database
from odoo import http
from werkzeug.exceptions import BadRequest

class MyDatabase(Database):

   
    @http.route()
    def drop(self, *args, **kwargs):    
        raise BadRequest()
    
              