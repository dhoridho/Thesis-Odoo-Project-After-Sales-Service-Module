odoo.define('equip3_pos_emenu.EmenuWebsite', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var core = require('web.core');
var _t = core._t;

var timeout;
var check_process_order_interval;
var check_payment_if_already_paid_interval;

publicWidget.registry.EmenuWebsite = publicWidget.Widget.extend({
    selector: '#emenu',
    events: { 
        'click .copy_clipboard': '_onClickCopyClipboard',
        'click .emenu-categories .item': '_onClickCategory',
        'click .emenu-search-form .search-clear': '_onClickClearSearch',
        'click .emenu-btn-order': '_onClickOpenBill',

        //Product Details
        'click .emenu-products .product-add-qty': '_onClickOpenProductDetail',
        'click .emenu-product-detail .add-quantity-button': '_onClickProductDetailAddQty',
        'click .emenu-product-detail .js_variant_change': '_onClickProductDetailChangeVariant',
        'click .emenu-product-detail .product-add-cart .add-cart': '_onClickProductDetailAddCart',

        //Cart
        'click .cart_info_button': '_onClickOpenCart',
        'change .cart .change-qty .add-quantity-input': '_onChangeCartChangeQtyInput',
        'click .cart .change-qty .add-quantity-button': '_onClickCartChangeQtyButton',
        'click .cart .payment-action .submit-order': '_onClickCartSubmitOrder',

        //Bill/Order Overview
        'click .bill .payment-action .payment-order': '_onClickBillPayment',

        //Payment
        'click .payment .payment-cashier-button': '_onClickProceedPayment',


    },

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
    },
    
    /**
     * @override
     */
    start: function () {
    	if(this.$el.hasClass('submit_order')){
    		this._check_process_order();
    	}
    	if(this.$el.hasClass('processed_order')){
    		this._check_processed_order();
    	}
    	if(this.$el.hasClass('payment_done')){
    		this._check_payment_if_already_paid();
    	}
        return this._super.apply(this, arguments);
    },

    /**
     * @private
     */
    _show_popup: function (template_url) {
		let $popup = $(`
			<div class="popups popup_cart" style="display: none;">
                <div class="spinner-wrapper">
	                <div class="spinner-border" role="status">
	                  <span class="sr-only">Loading...</span>
	                </div>
                </div
			</div>
		`)
		$('body > .emenu').append($popup);
		$popup.fadeIn(300);

		$.ajax({
	        type: 'POST',
			url: template_url,
	        success: function(template) {
				let content = `
					<div class="wrapper">
						<div class="back-button"></div>
						${ template }
					</div>
				`;
				$popup.find('.spinner-wrapper').replaceWith(content);
				$popup.find('.back-button').click(function (e) {
					e.preventDefault();
					$popup.fadeOut(300);
					setTimeout(function(){ $popup.remove() }, 400);
				});
	        },
	        error: function(response) {
	            console.error(response);
	        }
		});
    },
    
    /**
     * @private
     * @param {Event} ev
     */
    _onClickCopyClipboard: function (ev) {
        ev.preventDefault();
        let $el = $(ev.currentTarget)
		let copyText = $el.attr('data-copy_clipboard');
		let $temp = $('<input>');
		$('body').append($temp);
		$temp.val(copyText).select();
		document.execCommand('copy');
		$temp.remove();
		alert('Copied Transaction ID');
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onClickCategory: function (ev) {
        ev.preventDefault();
        let $el = $(ev.currentTarget)
		$el.parent().find('.item').removeClass('active');
		$el.addClass('active')
		let id = $el.attr('target');
		if(!id){ return; }
	   	document.getElementById(id).scrollIntoView( {behavior: "smooth" });
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onClickClearSearch: function (ev) {
        ev.preventDefault();
        let $el = $(ev.currentTarget);
		let $form = $el.closest('.emenu-search-form');
		$form.find('[name="search"]').val('');
		$form.submit();
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onClickOpenBill: function (ev) { 
        let $el = $(ev.currentTarget);
		let access_token = $el.closest('.home').attr('data-access_token'); 
		this._show_popup('/emenu/bill/' + access_token);
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onClickOpenProductDetail: function (ev) {
        ev.preventDefault();
        let $el = $(ev.currentTarget);
		let $parent = $el.closest('.product');
		let product_tmpl_id = $parent.attr('data-product_tmpl_id');
		let emenu_order_id = $parent.attr('data-emenu_order_id');
		this._show_popup('/emenu/product/' + emenu_order_id + '/' + product_tmpl_id);
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onClickProductDetailAddQty: function (ev) {
        ev.preventDefault();
        let $el = $(ev.currentTarget);
		let $parent = $el.closest('.emenu-product-detail');
		let $i = $el.closest('.add-quantity-action').find('.add-quantity-input');
		let val = parseInt($i.val());
		if($el.attr('type') == 'minus'){
			val -= 1;
			if(val <= 0){ val = 1; }
		}else{
			val += 1;
		}
		$i.val(val);
		$parent.attr('data-product_qty', val);

		let product_price = $parent.attr('data-product_price');
		let currency_symbol = $parent.attr('data-currency_symbol');
		let price = product_price * val;
		price = new Intl.NumberFormat('id-ID', { maximumSignificantDigits: 3 }).format(price,);
		$parent.find('.total-payment .total-payment-price').text(currency_symbol + ' ' + price);
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onClickProductDetailChangeVariant: function (ev) {
        let $el = $(ev.currentTarget);
		let $i = $el;
		let $parent = $el.closest('.emenu-product-detail');
        let $add_qty_btn = $parent.find('.product-add-cart .add-cart');
		let $product = $i.closest('.emenu-product-detail');

		$add_qty_btn.addClass('block');

	 	let $attributes = $i.closest('.c-option-variants').find('input.js_variant_change:checked, select.js_variant_change option:selected');
        let attributeIds = _.map($attributes, function (elem) {
            return $(elem).data('value_id');
        });
        let combination = attributeIds.join(',');
       	$.ajax({
			url: '/emenu/get_product_variant_combination?combination=' + combination,
		}).done(function(resp_json) {
			let data = JSON.parse(resp_json);
		  	if(data.product_id){
		  		$product.attr('data-product_id', data.product_id)
		  	}
			$add_qty_btn.removeClass('block');
		});
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onClickProductDetailAddCart: function (ev) {
        ev.preventDefault();
        let $btn = $(ev.currentTarget);
		if($btn.hasClass('loading')){
			return;
		}
		$btn.addClass('loading');

		let $parent = $btn.closest('.emenu-product-detail');
		let emenu_order_id = parseInt($parent.attr('data-emenu_order_id'));
		let product_id = parseInt($parent.attr('data-product_id'));
		let product_tmpl_id = parseInt($parent.attr('data-product_tmpl_id'));
		let price = parseFloat($parent.attr('data-product_price'));
		let qty = parseInt($parent.find('.add-quantity-action .add-quantity-input').val());
		let note = $parent.find('.c-add-notes [name="notes"]').val();

		$.ajax({
	        type: 'POST',
			url: '/emenu/cart/' + emenu_order_id + '/add',
	        contentType: 'application/json',
	        dataType: 'json',
	        data: JSON.stringify({
				'product_id': product_id,
				'product_tmpl_id': product_tmpl_id,
				'qty': qty,
				'emenu_order_id': emenu_order_id,
				'price': price,
				'note': note
			}),
	        success: function(response) {
	            $btn.removeClass('loading');
	            let $info = '';
	            if(response && response.result && response.result.status == 'success'){
		            $info = $(`<div class="alert alert-primary" 
		            	role="alert" style="position: fixed;top:0;z-index:12;right:0;cursor:pointer;display:none;"
		            	>Successfully add Menu</div>`);
		            
	            	let cart_info = response.result.cart_info;
	            	if(cart_info){
	            		$('.emenu_cart_info').attr('data-item-count', cart_info.item_count);
	            		$('.emenu_cart_info .total-item-value > span').text(cart_info.item_count);
	            		$('.emenu_cart_info .price-info > span').text(cart_info.format_amount_total);
	            	}

	            	$btn.closest('.popups').find('.back-button').click(); // Close popup
	            }else{
		            $info = $(`<div class="alert alert-danger" 
		            	role="alert" style="position: fixed;top:0;z-index:12;right:0;cursor:pointer;display:none;"
		            	>Failed to add Menu</div>`);
	            }
	            
	            $('body > .emenu').append($info);
	            $info.fadeIn(300);
	            $info.click(function (e) { $info.fadeOut(300); });
	            setTimeout(function(){ $info.fadeOut(300) }, 2000);
	        },
	        error: function(response) {
	            $btn.removeClass('loading');
	            console.error('Error ~ ', response);
	            let $info = $(`<div class="alert alert-danger" 
	            	role="alert" style="position: fixed;top:0;z-index:12;right:0;cursor:pointer;display:none;"
	            	>Failed to add Menu</div>`);
	            $('body > .emenu').append($info);
	            $info.fadeIn(300);
	            $info.click(function (e) { $info.fadeOut(300); });
		        setTimeout(function(){ $info.fadeOut(300) }, 2000);
	        }
		});
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onClickOpenCart: function (ev) {
        ev.preventDefault();
        let $el = $(ev.currentTarget);
		let access_token = $el.closest('.home').attr('data-access_token');
		this._show_popup('/emenu/cart/' + access_token);
    },

	/**
     * @private
     */
    _on_change_qty: function ($el) {
		let qty = $el.val();
		let emenu_order_id = $el.closest('.cart-lines').attr('data-emenu_order_id');
		let emenu_order_line_id = $el.closest('.order-line').attr('data-order_line_id');

		let $cart = $el.closest('.cart');
		let $submit_btn = $cart.find('.payment-details .submit-order');
		$submit_btn.addClass('block');

		let $cart_line = $el.closest('.cart-line');
		let $order_line = $el.closest('.order-line');
		let data = JSON.stringify({
			'qty': qty,
			'emenu_order_line_id': emenu_order_line_id,
		});

		$.ajax({
	        type: 'POST',
			url: '/emenu/cart/' + emenu_order_id + '/update',
	        contentType: 'application/json',
	        dataType: 'json',
	        data: data,
	        success: function(response) {
				$submit_btn.removeClass('block');

				let result = response.result;
	            if(result && result.status == 'success'){
					$el.attr('old_value', result.data.qty);

	            	$cart.find('.payment-line-amount.line-subtotal>span').text(result.data.format_amount_total);
	            	$cart.find('.payment-line-amount.line-addition>span').text(result.data.format_amount_total);
	            	if(result.data.qty <= 0){
	            		$el.closest('.product.order-line').remove();
	            		if($cart_line.find('.product.order-line').length == 0){
	            			$cart_line.remove();
	            		}
	            	}
	            	let cart_info = result.data.cart_info;
	            	if(cart_info){
	            		$('.emenu_cart_info').attr('data-item-count', cart_info.item_count);
	            		$('.emenu_cart_info .total-item-value > span').text(cart_info.item_count);
	            		$('.emenu_cart_info .price-info > span').text(cart_info.format_amount_total);

	            		if(cart_info.format_subtotal_incl){
	            			$order_line.find('.line-subtotal>span').text(cart_info.format_subtotal_incl);
	            		}
	            	}
	            }else{
					$el.val($el.attr('old_value'));
		            let $info = $(`<div class="alert alert-danger" 
		            	role="alert" style="position: fixed;top:0;z-index:12;right:0;cursor:pointer;display:none;"
		            	>Failed Change Quantity</div>`);
		            $('body').append($info);
		            $info.fadeIn(300);
		            $info.click(function (e) { $info.fadeOut(300); });
			        setTimeout(function(){ $info.fadeOut(300) }, 2000);
	            }

	        },
	        error: function(response) {
	            console.error('Error ~ ', response);
				$submit_btn.removeClass('block');
				$el.val($el.attr('old_value'));

	            let $info = $(`<div class="alert alert-danger" 
	            	role="alert" style="position: fixed;top:0;z-index:12;right:0;cursor:pointer;display:none;"
	            	>Failed Change Quantity</div>`);
	            $('body').append($info);
	            $info.fadeIn(300);
	            $info.click(function (e) { $info.fadeOut(300); });
		        setTimeout(function(){ $info.fadeOut(300) }, 2000);
	        }
		});
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onChangeCartChangeQtyInput: function (ev) {
		this._on_change_qty($(ev.currentTarget));
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onClickCartChangeQtyButton: function (ev) {
        ev.preventDefault();
        let $el = $(ev.currentTarget);
		let $i = $el.parent().find('.add-quantity-input');
		let val = parseInt($i.val());
		if($el.attr('type') == 'minus'){
			val -= 1;
		}else{
			val += 1;
		}
		$i.val(val);
		this._on_change_qty($i);
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onClickCartSubmitOrder: function (ev) {
        ev.preventDefault();
        let $el = $(ev.currentTarget);
		let $cart = $el.closest('.cart');
		let access_token = $el.attr('data-access_token');
		let order_line_ids = _.map($cart.find('.product.order-line'), function (elem) {
            return $(elem).data('order_line_id');
        });
        let lines = order_line_ids.join(',');
		if(!lines){
			return false;
		}
		if($el.hasClass('loading')){
			return false;
		}
		$el.addClass('loading');
		let action_url = '/emenu/process-order/submit/' + access_token;
    	let $form = $(`
    		<form action="${action_url}">
			  <input type="hidden" name="lines" value="${lines}">
			  <input type="submit" value="Submit">
			</form>
    	`);
		$('body > .emenu').append($form);
		$form.submit();
    },

    /**
     * @private
     */
    _check_process_order: function(){
    	let self = this;
    	let $el = this.$el.find('.process_order');
    	let access_token = $el.attr('data-access_token')
    	let lines = $el.attr('data-lines');

    	function check(){
			$.ajax({
		        type: 'POST',
				url: '/emenu/process-order/submit/check/' + access_token,
		        contentType: 'application/json',
		        dataType: 'json',
		        data: JSON.stringify({ 'lines': lines, }),
		        success: function(resp) {
					let result = resp.result;
		            if(result && result.validated){
						clearInterval(check_process_order_interval);

						let action_url = '/emenu/process-order/processed/' + access_token;
		            	let $form = $(`
		            		<form action="${action_url}">
							  <input type="submit" value="Submit">
							</form>
		            	`);
						$('body > .emenu').append($form);
						$form.submit();
					}
		        },
		        error: function(response) {
		            console.error(response);
		        }
			});
    	}

		clearInterval(check_process_order_interval);
    	check_process_order_interval = setInterval(check, 2000);
		
    },

    /**
     * @private
     */
    _check_processed_order: function(){
    	let self = this;
    	let $el = this.$el.find('.process_order');
    	let access_token = $el.attr('data-access_token')

    	setTimeout(function(){
			let action_url = '/emenu/bill/' + access_token;
	    	let $form = $(`
	    		<form action="${action_url}">
				  <input type="submit" value="Submit">
				</form>
	    	`);
			$('body > .emenu').append($form);
			$form.submit();
    	}, 5000)
    },


    /**
     * @private
     */
    _check_payment_if_already_paid: function(){
    	let self = this;
    	let $el = this.$el.find('.payment');
    	let access_token = $el.attr('data-access_token');

    	function check(){
			$.ajax({
		        type: 'POST',
				url: '/emenu/payment/done/check/' + access_token,
		        contentType: 'application/json',
		        dataType: 'json',
		        data: JSON.stringify({ }),
		        success: function(resp) {
					let result = resp.result;
		            if(result && result.is_already_paid){
						clearInterval(check_payment_if_already_paid_interval);

						let action_url = '/emenu/payment/done/paid/' + access_token;
		            	let $form = $(`
		            		<form action="${action_url}">
							  <input type="submit" value="Submit">
							</form>
		            	`);
						$('body > .emenu').append($form);
						$form.submit();
					}
		        },
		        error: function(response) {
		            console.error(response);
		        }
			});
    	}

		clearInterval(check_payment_if_already_paid_interval);
    	check_payment_if_already_paid_interval = setInterval(check, 2000);
    },


    /**
     * @private
     * @param {Event} ev
     */
    _onClickBillPayment: function (ev) {
        ev.preventDefault();
        let $el = $(ev.currentTarget);
		let access_token = $el.attr('data-access_token');
		if($el.hasClass('loading')){
			return false;
		}
		$el.addClass('loading');
		let action_url = '/emenu/payment/' + access_token;
    	let $form = $(`
    		<form action="${action_url}">
			  <input type="submit" value="Submit">
			</form>
    	`);
		$('body > .emenu').append($form);
		$form.submit();
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onClickProceedPayment: function (ev) {
        ev.preventDefault();
        let $el = $(ev.currentTarget);
		let access_token = $el.attr('data-access_token');
		if($el.hasClass('loading')){
			return false;
		}
		$el.addClass('loading');

		$.ajax({
	        type: 'POST',
			url: '/emenu/payment/submit/' + access_token + '',
	        contentType: 'application/json',
	        dataType: 'json',
	        data: JSON.stringify({ }),
	        success: function(response) {
	            if(response && response.result && response.result.status == 'success'){
		            let action_url = '/emenu/payment/done/' + access_token;
			    	let $form = $(`
			    		<form action="${action_url}">
						  <input type="submit" value="Submit">
						</form>
			    	`);
					$('body > .emenu').append($form);
					$form.submit();
				}else{
		            $btn.removeClass('loading');
		            console.error('Error ~ ', response);
		            let $info = $(`<div class="alert alert-danger" 
		            	role="alert" style="position: fixed;top:0;z-index:12;right:0;cursor:pointer;display:none;"
		            	>Failed Proceed Payment</div>`);
		            $('body > .emenu').append($info);
		            $info.fadeIn(300);
		            $info.click(function (e) { $info.fadeOut(300); });
			        setTimeout(function(){ $info.fadeOut(300) }, 2000);
				}
	        },
	        error: function(response) {
	            $btn.removeClass('loading');
	            console.error('Error ~ ', response);
	            let $info = $(`<div class="alert alert-danger" 
	            	role="alert" style="position: fixed;top:0;z-index:12;right:0;cursor:pointer;display:none;"
	            	>Failed Proceed Payment</div>`);
	            $('body > .emenu').append($info);
	            $info.fadeIn(300);
	            $info.click(function (e) { $info.fadeOut(300); });
		        setTimeout(function(){ $info.fadeOut(300) }, 2000);
	        }
		});
    },

});

return publicWidget.registry.EmenuWebsite;

});