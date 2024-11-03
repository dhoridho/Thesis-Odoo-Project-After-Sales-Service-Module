odoo.define('equip3_pos_report.pos', function(require) {
	"use strict";
	const models = require('point_of_sale.models');
	const screens = require('point_of_sale.ProductScreen');
	const PaymentScreen = require('point_of_sale.PaymentScreenNumpad');
	const ActionpadWidget = require('point_of_sale.ActionpadWidget'); 
	const core = require('web.core');
	const gui = require('point_of_sale.Gui');
	const popups = require('point_of_sale.ConfirmPopup');
	const rpc = require('web.rpc');
	const Registries = require('point_of_sale.Registries');

	var QWeb = core.qweb;
	var _t = core._t;
	
	models.load_models({
		model: 'stock.location',
		fields: ['id', 'complete_name'],
		domain: function (self) {
            return ['|', '|', ['id', 'in', self.config.stock_location_ids], ['id', '=', self.config.stock_location_id[0]], ['id', 'in', self.default_location_src_of_picking_type_ids]];
        },
		loaded: function(self, locations){
			self.locations = locations;
		},
	});

	models.load_models({
		model:  'pos.session',
		fields: ['id', 'name', 'user_id', 'config_id', 'start_at', 'stop_at', 'sequence_number', 'payment_method_ids', 'cash_register_id', 'state'],
		domain: function(self){
            var domain = [
                ['state','in',['opening_control','opened']],
                ['rescue', '=', false],
            ];
            if (self.config_id){
            	domain.push(['config_id', '=', self.config_id]);
            }
            return domain;
        },
		loaded: function(self,pos_sessions){
			self.pos_sessions = pos_sessions
		},
	});
});
