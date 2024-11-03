# -*- coding: utf-8 -*-
from .models.ir_http import IrHttnew

from  odoo.addons.http_routing.models.ir_http import IrHttp
# 



def patch_http():
    ir_http = IrHttnew()
    IrHttp._handle_exception = classmethod(ir_http._handle_exception_custom)
    
    
    
    

    
    
    


