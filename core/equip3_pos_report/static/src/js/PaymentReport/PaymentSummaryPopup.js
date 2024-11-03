odoo.define('equip3_pos_report.PopupPaymentWidget', function(require) {
	'use strict';

	const Popup = require('point_of_sale.ConfirmPopup');
	const Registries = require('point_of_sale.Registries');
	const PosComponent = require('point_of_sale.PosComponent');

	class PopupPaymentWidget extends Popup {
		constructor() {
            super(...arguments);
            this.render_payment_summary();
        }

  		go_back_screen() {
			this.showScreen('ProductScreen');
			this.trigger('close-popup');
		}

		mounted(){
			var self = this;
			$('#dt_strt').hide();
			$('#dt_end').hide();
		}

		clickCurrentSession(){
			if ($('#pymnt_crnt_ssn').is(':checked')) {
				$('#strt_dt').hide();
				$('#end_dt').hide();
			}
			else{
				$('#strt_dt').show();
				$('#end_dt').show();
			}
		}

		async render_payment_summary(){
			$('#dt_strt').hide();
			$('#dt_end').hide();

			$('#pymnt_crnt_ssn').click(function() {
				if ($('#pymnt_crnt_ssn').is(':checked')) {
					$('#strt_dt').hide();
					$('#end_dt').hide();
				}
				else{
					$('#strt_dt').show();
					$('#end_dt').show();
				}
			});

			var self = this;
			var is_current_session = $('#pymnt_crnt_ssn').is(':checked')
			var pay_st_date = $('#pay_st_date').val()
			var pay_ed_date = $('#pay_ed_date').val()
			var smry_payment = $('#smry_payment').val()

			var order = this.env.pos.get_order();
			var curr_session = self.env.pos.config.current_session_id[0];
			var payment_summary = [];
			var cashier = this.env.pos.get_cashier();

			$('#dt_strt').hide();
			$('#dt_end').hide();

			if(is_current_session == true)	
			{
				await this.rpc({
					model: 'pos.report.payment', 
					method: 'get_crnt_ssn_payment_pos_order', 
					args: [1,smry_payment,cashier.user_id[0],curr_session,is_current_session,pay_st_date,pay_ed_date], 
				}).then(function(data){ 
					var payments = data[2];
					payment_summary = data[1];
					var final_total = data[0];
					
					self.trigger('close-popup');
					self.showTempScreen('PaymentReceiptWidget',{
						payment_summary:payment_summary,
						final_total:final_total,
						is_current_session:is_current_session,
						payments : payments,
						smry_payment : smry_payment,
					});
				});
			}
			else{
				if(!pay_st_date){
					$('#dt_strt').show()
					setTimeout(function() {$('#dt_strt').hide()},3000);
					return
				}
				else if(!pay_ed_date){
					$('#dt_end').show()
					setTimeout(function() {$('#dt_end').hide()},3000);
					return
				}
				else{

					await this.rpc({
						model: 'pos.report.payment', 
						method: 'get_crnt_ssn_payment_pos_order', 
						args: [1,smry_payment,cashier.user_id[0],curr_session,is_current_session,pay_st_date,pay_ed_date], 
					}).then(function(data){ 
						var payments = data[2];
						payment_summary = data[1];
						var final_total = data[0];
						
						self.trigger('close-popup');
						self.showTempScreen('PaymentReceiptWidget',{
							payment_summary:payment_summary,
							final_total:final_total,
							is_current_session:is_current_session,
							payments : payments,
							start_date_pay:pay_st_date,
							end_date_pay:pay_ed_date,
							smry_payment : smry_payment,
						});
					});
					return
				}

			}
		}
	}
	PopupPaymentWidget.template = 'PopupPaymentWidget';
	PopupPaymentWidget.defaultProps = {
		confirmText: 'Print',
		cancelText: 'Cancel',
		title: 'Payment Summary',
		};

	Registries.Component.add(PopupPaymentWidget);

	return PopupPaymentWidget;
});
