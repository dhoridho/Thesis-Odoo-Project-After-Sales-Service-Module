odoo.define('equip3_catering_operation.hide_form_view_edit_button', function (require) {
    "use strict";

    var FormController = require('web.FormController');

    FormController.include({
        updateButtons: function () {
            if (!this.$buttons) {
                return;
            }
            console.log("-----------buttons")
            if (this.footerToButtons) {
                var $footer = this.renderer.$el && this.renderer.$('footer');
                if ($footer && $footer.length) {
                    this.$buttons.empty().append($footer);
                }
            }
            //specify the model where you want to hide the edit 
            //button based on field value
            if (this.modelName === "catering.order") {  
          
                console.log(this); 
                // It will print a Json Object with all available 
                //data regarding your current view
                //In my case I had to check the sate field and 
                //I found the value of sate field in
                //this.renderer.state.data.state
            

                if (this.renderer.state.data.state == "order") {
                    this.$buttons.find('.o_form_button_edit')
                            .toggleClass('o_hidden', true);
                } else {
                    this.$buttons.find('.o_form_button_edit')
                            .toggleClass('o_hidden', false);
                }
            } else {
                this.$buttons.find('.o_form_button_edit')
                        .toggleClass('o_hidden', false);
            }
            var edit_mode = (this.mode === 'edit');
            this.$buttons.find('.o_form_buttons_edit')
                .toggleClass('o_hidden', !edit_mode);
            this.$buttons.find('.o_form_buttons_view')
                .toggleClass('o_hidden', edit_mode);

        },
    });
});