odoo.define('equip3_pos_online_grabfood.OnlineOrderRow', function (require) {
    'use strict';

    const OnlineOrderRow = require('equip3_pos_online_outlet.OnlineOrderRow');
    const Registries = require('point_of_sale.Registries');
    const field_utils = require('web.field_utils');
    const {useState} = owl.hooks;
    const core = require('web.core');
    const _t = core._t;
    const framework = require('web.framework');
     
    const OnlineOrderRowExt = (OnlineOrderRow) =>
        class extends OnlineOrderRow {
            constructor() {
                super(...arguments);
            } 

            async actionAcceptOrder(onlineOrder) {
	            super.actionAcceptOrder(onlineOrder);
                let self = this;
	            if(onlineOrder.order_from == 'grabfood'){
            		framework.blockUI();

	                this.updateOrder(onlineOrder, {
		                'manual_action': 'accept',
		                'status': 'Accepted',
		                'state': 'to pay',
	                });

	                await this.rpc({
	                    model: 'pos.online.outlet.order',
	                    method: 'action_accept_grabfood_order',
	                    args: [onlineOrder.id],
	                }).then(function (resp) { 
	                    if(resp.content.status == 'failed'){
	                        self.showPopup('ErrorPopup', {
	                            title: 'Error',
	                            body: resp.content.message,
	                        });
	                        self.resetBackStatus(onlineOrder);
	                    }
	                    // if(resp.status == 'success'){
	                    //     self.createOrder(onlineOrder);
	                    // }
	                });

            		framework.unblockUI();
	            }
            }

            async actionRejectOrder(onlineOrder){
	            super.actionRejectOrder(onlineOrder);
                let self = this;
	            if(onlineOrder.order_from == 'grabfood'){
            		framework.blockUI();

	                this.updateOrder(onlineOrder, {
		                'manual_action': 'reject',
		                'status': 'Rejected',
		                'state': 'cancel',
	                });

	                await this.rpc({
	                    model: 'pos.online.outlet.order',
	                    method: 'action_reject_grabfood_order',
	                    args: [onlineOrder.id],
	                }).then(function (resp) { 
	                    if(resp.content.status == 'failed'){
	                        self.showPopup('ErrorPopup', {
	                            title: 'Error',
	                            body: resp.content.message,
	                        });
	                        self.resetBackStatus(onlineOrder);
	                    }
	                });

            		framework.unblockUI();
	            }
            }

            async actionCreateOrder(onlineOrder){
                super.actionCreateOrder(onlineOrder);
	            if(onlineOrder.order_from == 'grabfood'){
		            if(onlineOrder.state == 'to pay'){
		                let pos_order = this.env.pos.get_order_list().filter((o)=>o.oloutlet_order_id==onlineOrder.id);
		                if(pos_order.length == 0){
		                    let has_order = await this.createOrder(onlineOrder);
		                    if(!has_order){
		                    	return;
		                    }
		                }else{
		                    pos_order = this.env.pos.get('orders').models.find(o => o.uid == pos_order[0].uid)
		                    if (pos_order) {
		                        this.env.pos.set_order(pos_order, {});
		                    }
		                }

	            		this.trigger('close-screen');
	            		this.showScreen('ProductScreen', {selected_order_method: 'online-order'});
		            }
		        }
            }


            async actionChangeReadyTime(onlineOrder){
            	super.actionChangeReadyTime(onlineOrder);
                let self = this;
	            if(onlineOrder.order_from == 'grabfood'){
					let {confirmed, payload: payload} = await this.showPopup('OnlineOrderReadyTimePopup',{});
					if (confirmed) {
            			framework.blockUI();
						await this.rpc({
		                    model: 'pos.online.outlet.order',
		                    method: 'action_set_ready_time_grabfood_order',
		                    args: [onlineOrder.id],
		                    context: {  
		                    	'duration': payload.duration,
		                    }
		                }).then(function (resp) { 
		                	if(resp.content.status == 'success'){
		                		self.env.pos.alert_message({
					                title: 'Success',
					                body: 'Ready time successfully updated'
					            })
		                	}
		                    if(resp.content.status == 'failed'){
		                        self.showPopup('ErrorPopup', {
		                            title: 'Cannot change order ready time' + ' ('+onlineOrder.order_number+')',
		                            body: resp.content.message,
		                            cancelText: '',
		                            confirmText: 'OK',
		                        });
		                        self.resetBackStatus(onlineOrder);
		                    }
		                });
            			framework.unblockUI();
					}
				}
            }

            async actionMarkOrderReady(onlineOrder){
            	super.actionMarkOrderReady(onlineOrder);
                let self = this;
	            if(onlineOrder.order_from == 'grabfood'){
	            	const { confirmed } = await this.showPopup('ConfirmPopup', {
                        title: this.env._t('Confirmation'),
                        body: 'Are you sure want to mark this order ready?',
                    });
                    if (confirmed) {
		            	framework.blockUI();

		                this.updateOrder(onlineOrder, {
			                'is_mark_order_ready': true,
		                });

		                await this.rpc({
		                    model: 'pos.online.outlet.order',
		                    method: 'action_mark_ready_grabfood_order',
		                    args: [onlineOrder.id],
		                }).then(function (resp) { 
		                    if(resp.content.status == 'failed'){
		                        self.showPopup('ErrorPopup', {
		                            title: 'Error',
		                            body: resp.content.message,
		                        });
		                        self.resetMarkOrderReady(onlineOrder);
		                    }
		                });

	            		framework.unblockUI();
	            	}
	            }
            }

	        async createOrder(onlineOrder) {
            	super.createOrder(onlineOrder);
	            if(onlineOrder.order_from == 'grabfood'){
		            if((this.env.pos.tables != 'undefined') == false){
		                if(this.env.pos.tables[0]){
		                    this.env.pos.set_table(this.env.pos.tables[0]);
		                }
		            }
		            let orderLines = this.getOnlineOrderLines(onlineOrder);
		            
		            for(let line of orderLines){ 
		                let product = this.env.pos.db.get_product_by_id(line.product_id[0]);
		                if(typeof product == 'undefined'){
		                    this.showPopup('ErrorPopup', {
		                        title: 'Error',
		                        body: 'Product ' 
		                        	+ line.product_id[1] 
		                        	+ '('+ line.product_id[0] +')' 
		                        	+' is undefined',
		                    });
		                    console.error('Error line:', product, line);
		                    console.log('pos.db.product_by_id:', this.env.pos.db.product_by_id);
		                    return false;
		                }
		                if(product == false){
		                    this.showPopup('ErrorPopup', {
		                        title: 'Error',
		                        body: 'Product ID is not found, maybe already deleted / archived / Product categories is restricted'
		                        	+ ' (online_outlet_order_line_id:'+ line.id +')' ,
		                    });
		                    console.error('Error line:', product, line);
		                    console.log('pos.db.product_by_id:', this.env.pos.db.product_by_id);
		                    return false;
		                }
		            }
					
	                this.env.pos.add_new_order();
					let order = this.env.pos.get_order();

					let method = $('.pos').attr('data-selected-order-method');
					if(method == 'dine-in'){
						if(order === null){
		                    this.showPopup('ErrorPopup', {
		                        title: 'Warning',
		                        body: 'Please select table first before continue!',
		                    });
		                    return false;
						}
					}
		            order.is_online_outlet = true;
		            order.oloutlet_order_id = onlineOrder.id;
		            order.oloutlet_order_type = onlineOrder.order_type;
		            order.oloutlet_order_info = onlineOrder.info;

		            for(let line of orderLines){ 
		            	let price = line.price;
		                let options = {
		                    quantity: line.qty,
		                    price: price,
		                    force_price_price: price,
		                    discount: 0,
		                    merge: false,
		                }
		                let product = this.env.pos.db.get_product_by_id(line.product_id[0]);
	            		//Remove taxes
	                    if(!this.env.pos.product_taxes_id){
	                        this.env.pos.product_taxes_id = {}
	                    }
	                    if(product['taxes_id']){
	                        this.env.pos.product_taxes_id[product.id] = product['taxes_id'];
	                    }
		                product['taxes_id'] = []; // remove tax

		                order.add_product(product, options);
		            }
		            return order;
		        }
        	}
        }

    Registries.Component.extend(OnlineOrderRow, OnlineOrderRowExt);
    return OnlineOrderRow;

});