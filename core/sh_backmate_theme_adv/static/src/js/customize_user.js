odoo.define('sh_backmate_theme_adv.UserMenu', function (require) {
    "use strict";
    var UserMenu = require('web.UserMenu');
    var rpc = require('web.rpc')
    UserMenu.include({
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                rpc.query({
                    model: 'sh.back.theme.config.settings',
                    method: 'search_primary_var_template',
                    args: [[]],
                }, {async: false}).then(function(output) {
                    if(output){
                        self.$el.find("#night_checkbox").prop( "checked", true );
                    }else{
                        self.$el.find("#night_checkbox").prop( "checked", false );
                    }
                });
            });
        },
    })

});
