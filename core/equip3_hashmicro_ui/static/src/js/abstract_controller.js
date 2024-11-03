odoo.define('equip3_hashmicro_ui.AbstractController', function(require){
    "use strict";
    
    var AbstractController = require('app_search_range_date_number.AbstractController');
    var core = require('web.core');
    var extras = require('equip3_hashmicro_ui.Extras');
    
    AbstractController.include({

        events: _.extend({}, AbstractController.prototype.events, {
            'click .o_search_panel_toggler': '_onSearchPanelTogglerClick',
        }),

        start: function(){
            var self = this;
            core.bus.on('DOM_updated', this, () => extras.repositionFilters());
            core.bus.on('resize', this, () => extras.resizeSarchBar());
            return this._super.apply(this, arguments).then(function(){
                self.$el.find('.o_no_prop').on('click', function(ev){ev.stopPropagation();});
            });
        },

        _onSearchPanelTogglerClick: function(ev){
            extras.onSearchPanelTogglerClick(ev);
        },
    });
    
    return AbstractController;
});