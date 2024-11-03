odoo.define('equip3_hashmicro_ui.ControlPanel', function(require){
    "use strict";

    const ControlPanel = require('app_search_range_date_number.ControlPanel');
    const SearchMenu = require("equip3_hashmicro_ui.SearchMenu");
    const SearchBar = require("equip3_hashmicro_ui.SearchBar");
    const FavoriteMenu = require("equip3_hashmicro_ui.FavoriteMenu");

    ControlPanel.patch("equip3_hashmicro_ui.ControlPanel", (T) => {
        class appControlPanel extends T {

            _attachAdditionalContent() {
                super._attachAdditionalContent(...arguments);
                this._calculateHeight();

                if (window.matchMedia("(max-width: 992px)").matches) {
                    $('#o_equip_filter_dropdown').html(function() {
                        // Return only the content inside the <span> element
                        return $(this).find('span').html();
                    });

                    $('.o_cp_bottom').click(function(){
                       $('.o_searchview_input_container').css('top', '-15%');
                    });
                }
                $('.o_filters_toggler').click(function(){
                    if(!$(this).hasClass('alreadySetOnclick')){
                        $('.o_equip_search_filters_dropdown_menu').toggleClass('show');
                    }
                   
                });
            }

            _calculateHeight(){
                var $controlPanel = $('.o_control_panel');
                $controlPanel.css('min-height', 'unset');

                if($('.app-search-range-date select > option').length === 0 && $('.app-search-range-number select > option').length === 0){
                    $('.o_search_panel_toggler').hide();
                } else {
                    $('.o_search_panel_toggler').show();
                }
                if (this.env.view){
                    if (this.env.view.type === 'form'){
                        $controlPanel.css('padding', '5px 23px');
                    } else {
                        $controlPanel.css('padding', '5px 10px');
                    }
                }
            }
        }
        return appControlPanel;
    });

    ControlPanel.components = _.extend(ControlPanel.components, {SearchBar, SearchMenu, FavoriteMenu})
    return ControlPanel;
});
