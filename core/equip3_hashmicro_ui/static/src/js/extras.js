odoo.define('equip3_hashmicro_ui.Extras', function(require){

    var repositionFilters = function(){
        let $filters = $('.o_cp_top_top');
        if ($filters.length){
            let isModal = $('.modal-body.o_act_window').length > 0;
            if (isModal == false){
                let $systray = $('.o_main_navbar > .o_menu_systray');
                let right = isModal ? 0 : $systray.outerWidth();
                $filters.css('right', String(parseInt(right) - 10) + 'px');
            }
        }
    }

    var onSearchPanelTogglerClick = function(ev){
        let $arrow = $(ev.currentTarget).find('.o_search_panel_arrow i');
        $('.app-search-panel').toggleClass('o_search_panel_hide');
        if ($arrow.hasClass('fa-chevron-right')){
            $arrow.removeClass('fa-chevron-right');
            $arrow.addClass('fa-chevron-left');
        } else {
            $arrow.addClass('fa-chevron-right');
            $arrow.removeClass('fa-chevron-left');
        }
    }

    var resizeSarchBar = function(){
        let dropdownMenu = document.getElementsByClassName('parent_menu_autocomplete_dropdown');
        let cpTopTop = document.getElementsByClassName('o_cp_top_top');
        if (dropdownMenu.length === 0 || cpTopTop.length === 0){
            return;
        }
        let rect1 = dropdownMenu[0].getBoundingClientRect();
        let rect2 = cpTopTop[0].getBoundingClientRect();
        let offset = (rect1.x + rect1.width + 10) - rect2.x;
        let maxWidth = (40 * screen.width) / 100;
        let width = $(cpTopTop[0]).outerWidth() - offset;
        // $(cpTopTop[0]).css('width', width > maxWidth ? maxWidth : width + 'px');
    }

    return {
        repositionFilters: repositionFilters,
        onSearchPanelTogglerClick: onSearchPanelTogglerClick,
        resizeSarchBar: resizeSarchBar
    };

});