odoo.define('sh_price_checker_kiosk.kiosk_mode', function (require) {
"use strict";

var AbstractAction = require('web.AbstractAction');
var ajax = require('web.ajax');
var core = require('web.core');
var Session = require('web.session');

var QWeb = core.qweb;

var KioskMode = AbstractAction.extend({
    events: {
        "click .o_mrp_kiosk_button_done": function(){      	        
        /* Assignments and Validations When Go */
        var mo_no = $("#code").val();
        if(mo_no)
        {
        	/* Actions */
        	this._rpc({
		                model: 'product.product',
		                method: 'all_scan_search',
		                args: [mo_no],
		            })
		            .then(function (result) {
		            	if(result.issuccess==1){
		            		/* success msg */
		            			if ($('#display_landscape').val()=='left' || $('#display_landscape').val()=='right'){
		            				$('#screen_div').removeClass("col-12");
			            			$('#screen_div').addClass("col-7");
			            			$('#specification_div').removeClass("o_hidden");
		            			}
				            	$("#main_div").removeClass("o_hidden");   
				            	$("#sh_product_name").html(result.sh_product_name);
				            	$("#sh_product_code").html(result.sh_product_code);
				            	$('#sh_product_image').html('');
				            	$('#sh_product_image').append(
				            			'<img class="img img-responsive" width="auto !important;" style="max-height:100%;max-width:100%;" src="data:image/jpeg;base64,' + result.sh_product_image + '" alt="Product Image" />'
		                        );
				            	$("#sh_product_barcode").html(result.sh_product_barcode);
				            	$("#sh_product_sale_price").html(result.sh_product_sale_price);
				            	$("#sh_product_stock").html(result.sh_product_stock);
				            	$("#sh_product_category").html(result.sh_product_category);
								$("#sh_pricelist").html(result.sh_product_pricelist);
				            	if (result.sh_product_attribute == ''){
				            		$('#attribute_tr').addClass('o_hidden');
				            	}
				            	else if (result.sh_product_attribute != ''){
				            		$('#attribute_tr').removeClass('o_hidden');
				            		$("#sh_product_attribute").html(result.sh_product_attribute);
				            	}
				            	if (result.sh_product_sale_description == ''){
				            		$('#sale_description_tr').addClass('o_hidden');
				            	}
				            	else if (result.sh_product_sale_description != ''){
				            		$('#sale_description_tr').removeClass('o_hidden');
				            		$("#sh_product_sale_description").html(result.sh_product_sale_description);
				            	}
				            	$("#success").css("display","block");
		            			$("#success").html(result.msg);
		            			$("#fail").css("display","none");
								$("#code").val("");
								if(self.myvar){
				            		clearTimeout(self.myvar);
				            	}
				            	var delay =  $('#screen_delay').val() * 1000;
			            		   self.myvar = setTimeout(function(){
			            			   if ($('#display_landscape').val()=='left' || $('#display_landscape').val()=='right'){
					            			$('#screen_div').addClass("col-12");
					            			$('#screen_div').removeClass("col-7");
					            		}
					            		$("#main_div").addClass("o_hidden");
					            		$("#success").css("display","none");
			            		   },delay);
		            	}
		            	else{
		            		/* Fail msg */
		            		if ($('#display_landscape').val()=='left' || $('#display_landscape').val()=='right'){
		            			$('#screen_div').addClass("col-12");
		            			$('#screen_div').removeClass("col-7");
		            		}
		            		$("#main_div").addClass("o_hidden");
		            		$("#success").css("display","none");
		            		$("#fail").css("display","block");		            
		            		$("#fail").html(result.msg);
							$("#code").val("");
		            	}		                

		                /* Clear Inputs after result */
				        var mo_no = $("#mono").val("");				        		                		                		                		                
		            });		            
        }
        
        else{
        	alert("Please Enter Any barcode number");
        }
        
        }, 
        
    },

    start: function () {
        var self = this;   
        self.myvar = false;
        core.bus.on('barcode_scanned', this, this._onBarcodeScanned);
        self.session = Session;
        this._rpc({
                model: 'res.company',
                method: 'search_read',
                args: [[['id', '=', self.session.company_id]], 
                ['name','sh_product_code','sh_product_barcode','sh_product_sale_description','sh_product_sale_price','sh_touch_kyboard',
                'sh_product_stock','sh_product_attribute','sh_product_image','sh_product_category','sh_welcome_message','sh_message','sh_company_logo',
                'sh_display','sh_display_view','sh_display_landscape','sh_display_portrait','sh_delay_screen'
                ]],
            })
            .then(function (companies){
                self.company_name = companies[0].name;
                self.sh_product_code = companies[0].sh_product_code;
                self.sh_product_barcode = companies[0].sh_product_barcode;
                self.sh_product_sale_description = companies[0].sh_product_sale_description;
                self.sh_product_sale_price = companies[0].sh_product_sale_price;
                self.sh_touch_kyboard = companies[0].sh_touch_kyboard;
                self.sh_product_stock = companies[0].sh_product_stock;
                self.sh_product_attribute = companies[0].sh_product_attribute;
                self.sh_product_image = companies[0].sh_product_image;
                self.sh_product_category = companies[0].sh_product_category;
                self.sh_welcome_message = companies[0].sh_welcome_message;
                self.sh_message = companies[0].sh_message;
                self.sh_company_logo = companies[0].sh_company_logo;
                self.sh_display = companies[0].sh_display;
                self.sh_display_view = companies[0].sh_display_view;
                self.sh_display_landscape = companies[0].sh_display_landscape;
                self.sh_display_portrait = companies[0].sh_display_portrait;
                self.sh_delay_screen = companies[0].sh_delay_screen;
                self.company_image_url = self.session.url('/web/image', {model: 'res.company', id: self.session.company_id, field: 'logo',});
                self.$el.html(QWeb.render("MrpKioskKioskMode", {widget: self}));
                self.start_clock();
            });
        return self._super.apply(this, arguments);
    },

    _onBarcodeScanned: function(barcode) {
			var stage = $("#selstage").val();				
        	/* Actions */  
			var mo_no = $("#code").val();
			var self = this;
			core.bus.off('barcode_scanned', this, this._onBarcodeScanned);
        	this._rpc({
		                model: 'product.product',
		                method: 'all_scan_search',
		                args: [barcode],
		            })
		            .then(function (result) {
		            	if(result.issuccess==1){
		            		/* success msg */ 
		            		if ($('#display_landscape').val()=='left' || $('#display_landscape').val()=='right'){
	            				$('#screen_div').removeClass("col-12");
		            			$('#screen_div').addClass("col-7");
		            			$('#specification_div').removeClass("o_hidden");
	            			}
		            			$("#main_div").removeClass("o_hidden");
		            			$("#sh_product_name").html(result.sh_product_name);
				            	$("#sh_product_code").html(result.sh_product_code);
				            	$('#sh_product_image').html('');
				            	$('#sh_product_image').append(
			            			      '<img class="img img-responsive" width="auto !important;" style="max-height:100%;max-width:100%;" src="data:image/jpeg;base64,' + result.sh_product_image + '" alt="Product Image" />'
					                        );
				            	$("#sh_product_barcode").html(result.sh_product_barcode);
				            	$("#sh_product_sale_price").html(result.sh_product_sale_price);
				            	$("#sh_product_stock").html(result.sh_product_stock);
				            	$("#sh_product_category").html(result.sh_product_category);
				            	console.log(result.sh_product_attribute);
				            	if (result.sh_product_attribute == ''){
				            		$('#attribute_tr').addClass('o_hidden');
				            	}
				            	else if (result.sh_product_attribute != ''){
				            		$('#attribute_tr').removeClass('o_hidden');
				            		$("#sh_product_attribute").html(result.sh_product_attribute);
				            	}
				            	if (result.sh_product_sale_description == ''){
				            		$('#sale_description_tr').addClass('o_hidden');
				            	}
				            	else if (result.sh_product_sale_description != ''){
				            		$('#sale_description_tr').removeClass('o_hidden');
				            		$("#sh_product_sale_description").html(result.sh_product_sale_description);
				            	}
				            	$("#success").css("display","block");
		            			$("#success").html(result.msg);
		            			$("#fail").css("display","none");
								$("#code").val("");
								if(self.myvar){
				            		clearTimeout(self.myvar);
				            	}
				            	var delay =  $('#screen_delay').val() * 1000;
			            		   self.myvar = setTimeout(function(){
			            			   if ($('#display_landscape').val()=='left' || $('#display_landscape').val()=='right'){
					            			$('#screen_div').addClass("col-12");
					            			$('#screen_div').removeClass("col-7");
					            		}
					            		$("#main_div").addClass("o_hidden");
					            		$("#success").css("display","none");
			            		   },delay);
		            	}
		            	else{
		            		/* Fail msg */
		            		if ($('#display_landscape').val()=='left' || $('#display_landscape').val()=='right'){
		            			$('#screen_div').addClass("col-12");
		            			$('#screen_div').removeClass("col-7");
		            		}
		            		$("#main_div").addClass("o_hidden");
		            		$("#success").css("display","none");
		            		$("#fail").css("display","block");		            
		            		$("#fail").html(result.msg);	
							$("#code").val("");
		            	}		                

		                /* Clear Inputs after result */

				                    		                		                		                
		            });	
        	core.bus.on('barcode_scanned', this, this._onBarcodeScanned);
    },

    start_clock: function() {
        this.clock_start = setInterval(function() {this.$(".o_price_chekcer_clock").text(new Date().toLocaleTimeString(navigator.language, {hour: '2-digit', minute:'2-digit'}));}, 500);
        // First clock refresh before interval to avoid delay
        this.$(".o_price_chekcer_clock").text(new Date().toLocaleTimeString(navigator.language, {hour: '2-digit', minute:'2-digit'}));
    },

    destroy: function () {
        core.bus.off('barcode_scanned', this, this._onBarcodeScanned);
        clearInterval(this.clock_start);
        this._super.apply(this, arguments);
    },
});

core.action_registry.add('checker_kiosk_kiosk_mode', KioskMode);

return KioskMode;

});
