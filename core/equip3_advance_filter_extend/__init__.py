from . import models
from odoo import api, fields, SUPERUSER_ID

def _settle_filter_pending_approval(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Filter SO
    model_name = 'sale.order'
    check_filter = env['ir.filters'].search([('is_filter_pending_my_approval','=',True),('model_id','=',model_name)],limit=1)
    if not check_filter:
    	new_model =  env['ir.model'].search([('model','=',model_name)],limit=1)
    	env['ir.filters'].create({
    		'name':'Pending My Approval',
    		'model_id':model_name,
    		'is_filter_pending_my_approval':True,
    		'new_model_id':new_model.id,
    		'user_ids':False,
    		'is_default':False,
    	})



    # Filter PO
    model_name = 'purchase.order'
    check_filter = env['ir.filters'].search([('is_filter_pending_my_approval','=',True),('model_id','=',model_name)],limit=1)
    if not check_filter:
    	new_model =  env['ir.model'].search([('model','=',model_name)],limit=1)
    	env['ir.filters'].create({
    		'name':'Pending My Approval',
    		'model_id':model_name,
    		'is_filter_pending_my_approval':True,
    		'new_model_id':new_model.id,
    		'user_ids':False,
    		'is_default':False,
    	})


    # Filter PR
    model_name = 'purchase.request'
    check_filter = env['ir.filters'].search([('is_filter_pending_my_approval','=',True),('model_id','=',model_name)],limit=1)
    if not check_filter:
    	new_model =  env['ir.model'].search([('model','=',model_name)],limit=1)
    	env['ir.filters'].create({
    		'name':'Pending My Approval',
    		'model_id':model_name,
    		'is_filter_pending_my_approval':True,
    		'new_model_id':new_model.id,
    		'user_ids':False,
    		'is_default':False,
    	})


    # Filter AM
    model_name = 'account.move'
    check_filter = env['ir.filters'].search([('is_filter_pending_my_approval','=',True),('model_id','=',model_name)],limit=1)
    if not check_filter:
    	new_model =  env['ir.model'].search([('model','=',model_name)],limit=1)
    	env['ir.filters'].create({
    		'name':'Pending My Approval',
    		'model_id':model_name,
    		'is_filter_pending_my_approval':True,
    		'new_model_id':new_model.id,
    		'user_ids':False,
    		'is_default':False,
    	})


    # Filter PS
    model_name = 'product.supplierinfo'
    check_filter = env['ir.filters'].search([('is_filter_pending_my_approval','=',True),('model_id','=',model_name)],limit=1)
    if not check_filter:
    	new_model =  env['ir.model'].search([('model','=',model_name)],limit=1)
    	env['ir.filters'].create({
    		'name':'Pending My Approval',
    		'model_id':model_name,
    		'is_filter_pending_my_approval':True,
    		'new_model_id':new_model.id,
    		'user_ids':False,
    		'is_default':False,
    	})


    # Filter SP
    model_name = 'stock.picking'
    check_filter = env['ir.filters'].search([('is_filter_pending_my_approval','=',True),('model_id','=',model_name)],limit=1)
    if not check_filter:
    	new_model =  env['ir.model'].search([('model','=',model_name)],limit=1)
    	env['ir.filters'].create({
    		'name':'Pending My Approval',
    		'model_id':model_name,
    		'is_filter_pending_my_approval':True,
    		'new_model_id':new_model.id,
    		'user_ids':False,
    		'is_default':False,
    	})
