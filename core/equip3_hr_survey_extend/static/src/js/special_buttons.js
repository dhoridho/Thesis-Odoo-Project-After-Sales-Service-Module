const OUTLET_ADD_BUTTON= ".add-market-place-button";
const OUTLET_BACK_BUTTON=".outlet-back-button";
const OUTLET_DISCONNECT_BUTTON=".outlet-disconnect-button";

console.log("aa123")

/*var div = document.createElement("div");   // Create a <button> element
div.innerHTML = "<div t-name='button-back-template'>fsdfasf</div>";                   // Insert text
document.body.appendChild(div); ;*/
/*odoo.my_module = function(instance){
    var module = instance.web.list  // loading the namespace of  'web.list' 
    module.Column.include({         // include to  'web.list.Column' class
        value_check: function(){
           console.log("outlet_form_type123: " + outlet_form_type);
           return outlet_form_type;
        },        
    });
};*/
/*odoo.my_module = function(instance){
    instance.request_project = {};
    instance.request_project.back = function(){
        window.history.back();
    };
    instance.web.client_actions.add('bdt.back', 'instance.request_project.back');
    console.log("aa2")
  };*/
/*odoo.oepetstore = function(instance, local) {
    local.HomePage = instance.Widget.extend({
        template: "HomePageTemplate",
        init: function(parent) {
            this._super(parent);
            this.name = 0;
        },
        start: function() {
        },
    });

    instance.web.client_actions.add(
        'petstore.homepage', 'instance.oepetstore.HomePage');
}*/


/*odoo.define('pos_fnb_standard.menu.tree', function(require) {
    "use strict";
    var FormController = require("web.FormController");    
    var KanbanController = require("web.KanbanController");
    console.log(KanbanController);
    var ListController = require("web.ListController");
    var includeDict = {
        renderButtons: function () {
            this._super.apply(this, arguments);
            var self = this;
            if (!self.noLeaf && self.hasButtons) {
                self.$buttons.on('click', '.add-market-place-button', function () {
                    alert("a");
                    self._rpc({
                        route: '/web/action/load',
                        params: {
                            action_id: 'pos_fnb_standard.food_outlet_action',
                        },
                    })
                    .then(function(r) {
                        console.log(r);
                        return self.do_action(r);
                    });
                });
            }
            
        }
    };
    KanbanController.include(includeDict);
    /*FormController.include({
        _onButtonClicked: function (event) {
            console.log("aaa");
        if(event.data.attrs.id === "darkroom-save"){
        //your code
          //alert("a");
          console.log("aaaa");
        }
        this._super(event);
        },
        });
        KanbanController.include({
            _onButtonClicked: function (event) {
                console.log("aaa");
            if(event.data.attrs.id === "darkroom-save"){
            //your code
              //alert("a");
              console.log("aaaa");
            }
            this._super(event);
            },
            });  
    ListController.include(includeDict);
});*/
/*odoo.define('your_module_folder.JsToCallWizard', function (require) {

    "use strict";
    
    var KanbanController = require('web.KanbanController');
    
    var JsTocallWizard = KanbanController.include({
    
    renderButtons: function($node){
    
    this._super.apply(this, arguments);
    
    if (this.$buttons) {
    
    this.$buttons.on('click', '.add-market-place-button', function () {
    
    var self = this;
    
    self.do_action({
    
    name: "Open a wizard",
    
    type: 'ir.actions.act_window',
    
    res_model: 'my.wizard.model.name',
    
    view_mode: 'form',
    
    view_type: 'form',
    
    views: [[false, 'form']],
    
    target: 'new',
    
    });
    
    });
    
    //this.$buttons.appendTo($node);
    
    }
    
    },
    
    });
    
    });*/
    var outlet_form_type= "";

    odoo.define('pos_fnb_standard.actionJS', function (require) {
        "use strict";
         
        var KanbanController = require('web.KanbanController');
        var FormController = require('web.FormController');     
        //var Model = require('web.Model');
        var rpc = require('web.rpc');
        //console.log("a" + KanbanController);
        //var session = require('web.session');
        //console.log('session: ' + JSON.stringify(session));
        if (KanbanController!=null)
        {
            console.log("0");
            KanbanController.include({
                renderButtons: function ($node) {
                    $(document).ready(function () {
                        console.log('Vao document.ready');
                        //Tim toi add-market-place-button
                        var spanAddMarketPlace= $('.add-market-place-button').find('span')
                        if(spanAddMarketPlace!=null) {
                            console.log("found span inadd-market-place-button" + spanAddMarketPlace.length);
                            spanAddMarketPlace.text("Add");
                            // won't alert!
                        }   
                        
                     });
                     
                    this._super.apply(this, arguments);     
                    console.log("KanbanController-1");       
                    if (!this.noLeaf && this.hasButtons) {
                        console.log("KanbanController-2" + this.$buttons + "-" + $('button').find(OUTLET_ADD_BUTTON) ); 
                        if (this.$buttons && $('button').find(OUTLET_ADD_BUTTON))
                        {
                            console.log("KanbanController-3" + this.$buttons + "-" + $('button').find(OUTLET_ADD_BUTTON) ); 
                            this.$buttons.on('click', OUTLET_ADD_BUTTON, this._onBtnMultiUpdate.bind(this)); // add event listener
                        }                        
                    }
                },
                _onBtnMultiUpdate: function (ev) {
                    // we prevent the event propagation because we don't want this event to
                    // trigger a click on the main bus, which would be then caught by the
                    // list editable renderer and would unselect the newly created row
                    if (ev) {
                        ev.stopPropagation();
                    }
                    var self = this;

                    //alert("abc");
                    return self._rpc({
                        route: '/web/action/load',
                        params: {
                            action_id: 'pos_fnb_standard.add_market_place_action_window',
                        },
                    })
                    .then(function(r) {
                        console.log(r);
                        return self.do_action(r);
                    });                
                },
            });
        }
        if (FormController!=null)
        {
            console.log("FormController0");
            FormController.include({
                renderButtons: function ($node) {
                    this._super.apply(this, arguments);     
                    console.log("FormController1");       
                    if (!this.noLeaf && this.hasButtons) {
                        console.log("FormController2" + this.$buttons + "-" + $('button').find(OUTLET_BACK_BUTTON) ); 
                        if (this.$buttons && $('button').find(OUTLET_BACK_BUTTON))
                        {
                            console.log("FormController31" + this.$buttons + "-" + $('button').find(OUTLET_BACK_BUTTON) ); 
                            this.$buttons.on('click', OUTLET_BACK_BUTTON, this._onBtnMultiUpdate.bind(this, OUTLET_BACK_BUTTON)); // add event listener                        
                            //var btn = this.$buttons.find('.outlet-back-button')
                            
                            // PERFORM THE ACTION
                            //btn.on('click', this.proxy('do_new_button'))
                        }  
                        if (this.$buttons && $('button').find(OUTLET_DISCONNECT_BUTTON))
                        {
                            console.log("FormController32" + this.$buttons + "-" + $('button').find(OUTLET_DISCONNECT_BUTTON) ); 
                            this.$buttons.on('click', OUTLET_DISCONNECT_BUTTON, this._onBtnMultiUpdate.bind(this, OUTLET_DISCONNECT_BUTTON)); // add event listener
                        }                                                                        
                    }
                },
                /*do_new_button: function() {

                    /*instance.web.Model('sale.order')
                        .call('update_sale_button', [[]])
                        .done(function(result) {
                            console.log("form41");
                        }
                        var custom_model = new  Model('foodmarket.outlet');
                        custom_model.call('gotoBack');
                }, */               
                _onBtnMultiUpdate: function (buttonType, ev) {
                    // we prevent the event propagation because we don't want this event to
                    // trigger a click on the main bus, which would be then caught by the
                    // list editable renderer and would unselect the newly created row
                    console.log("buttonType: " + buttonType + "-" + ev);
                    if (ev) {
                        //ev.stopPropagation();
                    }
                    var self = this;
                    //var custom_model = new  Model('foodmarket.outlet');
                    //custom_model.call('gotoBack');

                    //return;
                    
                    //alert("abc");
                    let methodName= '';
                    if (buttonType==OUTLET_BACK_BUTTON)
                    {
                        methodName= 'gotoBack';
                        //console.log('window.history.back');
                        window.history.back();
                        return;
                        /*return self._rpc({
                            route: '/web/action/load',
                            params: {
                                action_id: 'pos_fnb_standard.food_outlet_action',
                            },
                        })
                        .then(function(r) {
                            console.log(r);
                            return self.do_action(r);
                        });  */
                    
                    }else if (buttonType==OUTLET_DISCONNECT_BUTTON)
                    {
                        methodName= 'executeDisconnect';
                    }
                    console.log('methodName' + methodName);

                    if (methodName!='')
                    {
                        return this._rpc({
                            model: 'foodmarket.outlet',
                            method: methodName,
                            args: [{
                                'arg1': "a"
                            }],
                            context: this.initialState.context,
                        }).then(function(result) {
                            // location.reload();
                            self.do_action(result);
                        });
                    }
                  
                    /*
                    return self._rpc({
                        route: '/web/action/load',
                        params: {
                            action_id: actionId,
                        },
                    })
                    .then(function(r) {
                        console.log(r);
                        return self.do_action(r);
                    });                */
                },
            });
        }

        var basic_fields = require('web.basic_fields');
        var registry = require('web.field_registry');
        console.log("cw1");
        // widget implementation
        var BoldWidget = basic_fields.FieldChar.extend({
            _renderReadonly: function () {
                //console.log("cw2:" + outlet_form_type);
                this._super();
                var old_html_render = this.$el.text();
                //alert(old_html_render);
                outlet_form_type= old_html_render;
                console.log("old_html_render:" + old_html_render);
                if (old_html_render=="1" || old_html_render=="2")
                {                  
                  var new_html_render = '<b style="color:white;">' + old_html_render + '</b>'
                  this.$el.html(new_html_render);
                  console.log("cw2-" + outlet_form_type);
                }
                var self = this;
                self.form_type = old_html_render;
                var core = require('web.core');
                var QWeb = core.qweb;
                /*QWeb.render('systray_odoo_search.search_result', {
                    widget: self
                })*/;
                //QWeb.render("HomePageTemplate", {name: old_html_render});
                /*var div = document.createElement("div");   // Create a <button> element
                btn.innerHTML = "<div t-name='button-back-template'>fsdfasf</div>";                   // Insert text
                document.body.appendChild(btn);*/  
                console.log("divBack.innerHTML-old_html_render=='1':" + (old_html_render=="1"));

                $(document).ready(function () {
                    console.log('Vao document.ready');
                    //Tim toi add-market-place-button
                    /*var spanAddMarketPlace= $('.add-market-place-button').find('span')
                    if(spanAddMarketPlace!=null) {
                        console.log("found span inadd-market-place-button" + spanAddMarketPlace.length);
                        spanAddMarketPlace.text("Add");
                        // won't alert!
                    }*/

                    if (old_html_render=="1"){
                        setTimeout(function(){ 
                            var divBack= document.getElementsByClassName("specialDivBackButton123");;//$( ".specialDivBackButton123");//document.getElementById("divBack");
                            var divBack1= document.getElementsByClassName("specialDivBackButton124");
                            console.log("divBack.innerHTML-divBack!=null:" + divBack.length);
                            console.log("divBack.innerHTML-divBack1!=null:" + divBack1.length);
                            if (divBack!=null && divBack.length>0)
                            {
                                console.log("divBack.innerHTML2:" + divBack.length);
                               
                                console.log("divBack.innerHTML2:" + divBack1.length);
                                divBack[0].style.display='block';
                                console.log("divBack.innerHTML3:" + divBack.innerHTML);  
                            } 
    
                         }, 0);
                                          
                    }else  if (old_html_render=="2"){
                        setTimeout(function(){ 
                            var divBack= document.getElementsByClassName("specialDivBackButton123");;//$( ".specialDivBackButton123");//document.getElementById("divBack");
                            var divBack1= document.getElementsByClassName("specialDivBackButton124");
                            console.log("divBack.innerHTML-divBack!=null:" + divBack.length);
                            console.log("divBack.innerHTML-divBack1!=null:" + divBack1.length);
                            if (divBack!=null && divBack.length>0)
                            {
                                console.log("divBack.length:" + divBack.length);
                               
                                console.log("divBack1.length:" + divBack1.length);
                                divBack[0].style.display='none';
                                //divBack[0].parentElement.style.display='none';
                                //divBack[0].parentElement.parentElement.style.display='none';    
                                //divBack[0].parentElement.parentElement.parentElement.style.display='none';    
                                //divBack[0].parentElement.parentElement.parentElement.parentElementstyle.display='none';    
                                //divBack[0].parentElement.parentElement.parentElement.parentElement.parentElement.style.display='none';                                    
                                console.log("divBack[0].parentElement.parentElement-tagname:" + divBack[0].parentElement.parentElement.tagName);                                                            
                            } 
                         }, 0);
                                          
                    }
                    
                    if (old_html_render=="1" || old_html_render=="2"){
                        setTimeout(function(){ 
                            var divEdit= document.getElementsByClassName("specialDivEditButton123");;//$( ".specialDivBackButton123");//document.getElementById("divBack");
                            console.log("divEdit.innerHTML-divEdit!=null:" + divEdit.length);
                            if (divEdit!=null && divEdit.length>0)
                            {
                                console.log("divEdit.innerHTML2:" + divBack.length);
                               
                                divEdit[0].style.display='none';
                                console.log("divEdit.innerHTML3:" + divEdit.innerHTML);  
                            } 
    
                         }, 0);                                      
                    }else{
                        setTimeout(function(){ 
                            var divEdit= document.getElementsByClassName("specialDivEditButton123");;//$( ".specialDivBackButton123");//document.getElementById("divBack");
                            console.log("divBack.innerHTML-divEdit!=null:" + divEdit.length);
                            if (divEdit!=null && divEdit.length>0)
                            {
                                console.log("divEdit.innerHTML2:" + divBack.length);
                               
                                divEdit[0].style.display='block';
                                console.log("divEdit.innerHTML3:" + divEdit.innerHTML);  
                            } 
    
                         }, 0);
                    }
                    console.log("old_html_render1:" + old_html_render);

                 });
               
 
            },
        });
        
        registry.add('bold_red', BoldWidget); // add our "bold" widget to the widget registry
         console.log("cw3");

    });

    /*odoo.define('pos_fnb_standard.result_field', function(require) {
        "use strict";
        var FieldChar = require('web.basic_fields').FieldChar;
        console.log('c1');
        var CustomFieldChar = FieldChar.extend({
            _renderEdit: function () {
                console.log('c2');
                // Override this function to modify your field editing
            }, 
            _renderReadonly: function () {
                console.log('c3');
                // implement some custom logic here
                this._super();
                var old_html_render = this.$el.html();
                var new_html_render = '<b style="color:red;">' + old_html_render + '</b>'
                this.$el.html(new_html_render);                
            },
        });

        var fieldRegistry = require('web.field_registry');

        fieldRegistry.add('mycustomfield', CustomFieldChar);
           // This is the name of your new widget field extending the Native Odoo NumericField
           //Registry.add('my_result_widget', ResultFieldFloat);    
     });
     */

     