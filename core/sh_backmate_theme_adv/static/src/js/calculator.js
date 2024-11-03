
// ===========================================
//	Calculator
// ===========================================

odoo.define('sh_backmate_theme_adv.calculator', function (require) {
    "use strict";

    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var Widget = require('web.Widget');
    var rpc = require('web.rpc');    
    var SystrayMenu = require('web.SystrayMenu');
    var _t = core._t;
    var QWeb = core.qweb;
    var session = require('web.session');
    var calculator = Widget.extend({
        template: "CalculatorTemplate",

        events: {
            'click .open_calc': 'click_calc',             
        },   
        click_calc: function () {
        	var qweb_data = QWeb.render("sh_backmate_theme_adv.CalcResults", {
              widget: this
          })
          if($('.calculator').length > 0){
        	  this.$(".sh_calc_results").html("");
          }else{
        	  this.$(".sh_calc_results").html(qweb_data);
          }
          if($('.sh_calc_util').hasClass('active')){
        	  $('.sh_calc_util').removeClass('active')
          }else{
        	  $('.sh_calc_util').addClass('active')
          }
        },

     
    });
    calculator.prototype.sequence = 10;
    session.user_has_group('sh_backmate_theme_adv.group_calculator_mode').then(function(has_group) {
    	if(has_group){
    		 SystrayMenu.Items.push(calculator);
    	}
    });
    
   

   //return calculator;
   return {
	   calculator: calculator,
   };
});