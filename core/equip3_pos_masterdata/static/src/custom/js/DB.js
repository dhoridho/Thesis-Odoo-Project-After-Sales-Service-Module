odoo.define('equip3_pos_masterdata.CustomDB', function (require) {
"use strict";

var core = require('web.core');
var utils = require('web.utils');
var PosDB = require('point_of_sale.DB');
	
	PosDB.include({
		init: function(options){
			this._super(options);
			this.pos_combos_by_id = {};
			this.pos_combos_items_by_id = {};
		},
		add_pos_combo:function(combos){
			for(var i = 0, len = combos.length; i < len; i++){
				var combo = combos[i];
				this.pos_combos_by_id[combo.id] = combo;
			}
		},
		add_pos_combo_items: function(combo_items){
			for(var i = 0, len = combo_items.length; i < len; i++){
				var combo_item = combo_items[i];
				this.pos_combos_items_by_id[combo_item.id] = combo_item;
			}
		},
		get_pos_combos_by_id(id){
			return this.pos_combos_by_id[id];
		},
		get_pos_combos_items_by_id(id){
			return this.pos_combos_items_by_id[id];
		},
		set_pos_device_id(pos_device_id){
			// 1 browser is only 1 device ID
			return localStorage.setItem('pos_device_id', pos_device_id); 
		},
		get_pos_device_id(model){
			// 1 browser is only 1 device ID
			return localStorage.getItem('pos_device_id');
		},

		get_state_load_models(model){
			let models = localStorage.getItem('pos_state_load_models');
			if(models){
				models = JSON.parse(models);
			} else {
				models = {}
			}

			if(models[model]){
				return true;
			}
			return false;
		},
		update_state_load_models(model){
			let models = localStorage.getItem('pos_state_load_models');
			if(models){
				models = JSON.parse(models);
			} else {
				models = {}
			}

			models[model] = true;
			localStorage.setItem('pos_state_load_models', JSON.stringify(models)); 
		}

	});
});