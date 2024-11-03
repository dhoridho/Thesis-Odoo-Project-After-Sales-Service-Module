odoo.define('equip3_pos_order_retail.DB', function (require) {
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
		}
	});
});