odoo.define('equip3_general_encrypt_url.ActWindowActionManager', function (require) {
"use strict";

/**
 * The purpose of this file is to add the support of Odoo actions of type
 * 'ir.actions.act_window' to the ActionManager.
 */

var ActionManager = require('web.ActionManager');
var config = require('web.config');
var Context = require('web.Context');
var core = require('web.core');
var pyUtils = require('web.py_utils');
var view_registry = require('web.view_registry');

ActionManager.include({
    loadState: function (state) {

        var _super = this._super.bind(this);
        var action;
        var options = {
            clear_breadcrumbs: true,
            pushState: false,
        };
        if(state.hashcode &&!core.action_registry.contains(state.action)){
            var context = {}
            var hashcode = state.hashcode.replace('!','=')
            hashcode = atob(decodeURIComponent(hashcode))
            state.res_id = parseInt(hashcode)
            context.params = state;
            action = state.action;
            options = _.extend(options, {
                    resID: parseInt(hashcode), 
                    res_id: parseInt(hashcode), 
                    hashcode_id : parseInt(hashcode), 
                    viewType: state.view_type,
                });
        }
        else if (state.model && state.hashcode) {
            var hashcode = state.hashcode.replace('!','=')
            hashcode = atob(decodeURIComponent(hashcode))

            action = {
                res_model: state.model,
                res_id: parseInt(hashcode),
                type: 'ir.actions.act_window',
                views: [[state.view_id || false, 'form']],
            };

            
        } 
        if (action) {
            return this.doAction(action, options);
        }
        return _super.apply(this, arguments);
    },


});

});
