odoo.define('simplify_access_management.action_items', function (require) {
"use strict";

var core = require('web.core');
var _t = core._t;

var ListController = require('web.ListController');
var FormController = require('web.FormController');

    ListController.include({
        willStart: function () {
            var def = this._super.apply(this, arguments);
            var self = this;
            self.action_to_remove = [];
            
            var def2 = self._rpc({
                model: 'access.management',
                method: 'get_remove_options',
                args: [self.id, this.modelName],
            }).then(function (remove_options) {

                self.action_to_remove =  remove_options;
            })
            return Promise.all([def,def2]);
        },
        _getActionMenuItems:function(state) {
            var sup = this._super.apply(this, arguments);
            if(sup){
                var menu_items = sup.items.other;
                if (this.action_to_remove && this.action_to_remove.length > 0){
                    if(menu_items){
                        this.action_to_remove.forEach(function(action) {
                            menu_items = _.reject(menu_items, function (item) {
                                return item.description === action;
                            });
                        });
                    }
                    sup.items.other = menu_items
                }
            }
            return sup
        }
    });
    FormController.include({
        willStart:function(){
            var def = this._super.apply(this, arguments);
            var self = this;
            self.action_to_remove = [];
            var def2 = self._rpc({
                model: 'access.management',
                method: 'get_remove_options',
                args: [self.id, this.modelName],
            }).then(function (remove_options) {

                self.action_to_remove =  remove_options;
            })
            return Promise.all([def,def2]);
        },
        _getActionMenuItems:function(state) {
            var sup = this._super.apply(this, arguments);
            if(sup){
                var menu_items = sup.items.other;
                if (this.action_to_remove && this.action_to_remove.length > 0){
                    if(menu_items){
                        this.action_to_remove.forEach(function(action) {
                            menu_items = _.reject(menu_items, function (item) {
                                return item.description === action;
                            });
                        });
                    }
                    sup.items.other = menu_items
                }
            }
            return sup
        }
    });
});
