odoo.define('equip3_hashmicro_ui.Menu', function (require) {
    "use strict";

    var Menu = require('web.Menu');
    var session = require('web.session');

    Menu.include({
        events: _.extend({}, Menu.prototype.events, {
            'change .parent_menu_option': '_onParentMenuChange',
            'click .action_menu': '_onMenuitemClick',
            'click .parent_menu_autocomplete': '_onInputClick',
            'click .search_dropdown': '_onInputClick',
            'input #appDrawerSearchInput': '_showFoundMenus',
            'click .close_sidebar': '_onCloseSidebar'
        }),

        init: function (parent, menu_data) {
            this._super.apply(this, arguments);
            this.currentMenu = false;
            this.lastrecordID = false;
            this.autoCompleteChange = false;
        },

        start: function () {
            this._super.apply(this, arguments);
            this.$appSelector = this._createAppSelector();
            this.$appSelector.appendTo($('.parent_menu_select'));
            this._setAutocomplete();
        },
        
        _setAutocomplete: function(){
            var self = this;
            var $input = $('.parent_menu_autocomplete');
            $input.autocomplete({
                classes: {
                    'ui-autocomplete': 'parent_menu_autocomplete_ui',
                },
                source: function (req, resp) {
                    const query = req.term.trim().toLowerCase();

                    var filteredApps = _.filter(self._appsMenu._apps, function(app){
                        return app.name.toLowerCase().includes(query);
                    });
                    if (!filteredApps.length){
                        filteredApps = self._appsMenu._apps;
                    }
                    resp(_.map(filteredApps, function (app) {
                        var category;
                        if (app.appdata && app.appdata.equip_category_id){
                            category = self._appsMenu.menuCategories[app.appdata.equip_category_id[0]];
                        }
                        return {
                            label: app.name,
                            value: app.menuID,
                            category: category
                        }
                    }));
                },
                select: function (event, ui) {
                    event.stopImmediatePropagation();
                    event.preventDefault();
                    $input.val(ui.item.label);
                    self.autoCompleteChange = true;
                    self.$appSelector.val(ui.item.value);
                    self.$appSelector.trigger('change');
                    return false;
                },
                focus: function (event) {
                    event.preventDefault();
                },
                maxResults: 5,
                minLength: 0
            });
            
            $input.autocomplete('instance')._renderItem = function( ul, item ){
                return $('<li class="o_menu_flag"><div><img src=/web/image?model=ir.ui.menu&amp;field=web_icon_data&amp;id='+item.value+'><span>'+item.label+'</span></div></li>').appendTo(ul);
            };
            $input.autocomplete('instance')._renderItemData = function( ul, item ){
                return this._renderItem( ul, item ).data( "ui-autocomplete-item", item );
            };
            $input.autocomplete('instance')._renderMenu = function( ul, items ) {
                var categories = {};
                _.each(items, function(item){
                    var category = item.category;
                    if (category){
                        if (!(category.id in categories)){
                            categories[category.id] = {
                                data: category,
                                items: [item]
                            };
                        } else {
                            categories[category.id].items.push(item);
                        }
                    }
                });
        
                var that = this;
                _.each(Object.values(categories), function(category) {
                    var li = $('<li class="o_menu_category col-4"><h3 style="color:'+category.data.color+';">'+category.data.name+'</h3></li>');
                    var ulChild = $('<ul class="o_hm_menu"></ul>');
                    ulChild.appendTo(li);
                    li.appendTo(ul);
                    
                    _.each(category.items, function(item) {
                        that._renderItemData(ulChild, item);
                    });
                });
            };
        
            $input.autocomplete('instance')._on('ul', {
                menufocus: function( event, ui ) {return;}
            })

            $input.autocomplete("option", "position", {my : "left top", at: "left bottom"});
        },

        _createAppSelector: function(){
            const $appSelector = $('<select></select>', {class: 'parent_menu_option'});
            _.each(this._appsMenu._apps, function(app) {
                const $option = $('<option></option>', {
                    'text': app.name,
                    'value': app.menuID,
                    'data-menu-id': app.menuID,
                    'data-menu-xmlid': app.xmlID,
                    'data-action-id': app.actionID
                });
                $option.appendTo($appSelector);
            })
            return $appSelector;
        },

        _onCloseSidebar: function(event) {
            event.stopPropagation();
            $('body').toggleClass('show_full_screen');
            $('.o_action_manager').toggleClass('closed');
            $('.close_sidebar').toggleClass('closed');
            $('.menu_image').toggleClass('closed');
            $('.parent_menu_autocomplete_dropdown').toggleClass('closed');
            $('body').find('.hover_menuitem > .dropdown-menu:not(.ag_sidebar_submenu)').toggleClass('closed');
        },

        _showFoundMenus: function(event) {
            event.stopPropagation();
            var search_term = $(event.target).val();
            var $current_ul = $('a[role="menuitem"].active').closest('.cssmenu').find('ul.dropdown-menu:not(.search_ul)');
            if ($current_ul.length  > 1) {
                $current_ul = $($current_ul[0])
            }
            var $hide_ul = $('.hide_menu');
            if (search_term != '') {
                if ($current_ul.length) {
                    $current_ul.addClass('hide_menu');
                    $current_ul.removeClass('show_ul');
                }
                else {
                    $current_ul = $hide_ul;
                }
                $current_ul.parent().find('.search_ul').removeClass('d-none');
                $current_ul.parent().find('.search_ul').html('');
                _.each($('a.action_menu'), function(element){
                    var $element = $(element);
                    var menu_name = $element.data('complete-name');
                    if (menu_name){
                        if (menu_name.toLowerCase().includes(search_term.toLowerCase())) {
                            let menu_item = $(element).clone(true);
                            menu_item.css('height', 'unset');
                            menu_item.css('min-height', '44px');
                            menu_item.html('<span style="word-break: break-word;">' + menu_name + '</span>');
                            let dropdown_header = $('<div class="dropdown-header">');
                            menu_item.appendTo(dropdown_header);
                            menu_item.addClass('search_menu');
                            $current_ul.parent().find('.search_ul').append(dropdown_header);
                        }
                    }
                });
            } else {
                $hide_ul.addClass('show_ul');
                $hide_ul.removeClass('hide_menu');
                $hide_ul.parent().find('.search_ul').addClass('d-none');
                $hide_ul.parent().find('.search_ul').html('');
            }
        },

        _onInputClick: function(event) {
            $('.parent_menu_autocomplete').autocomplete("search", '');
        },

        _onParentMenuChange: function(event) {
            $('#appDrawerSearchInput').val('');
            $('#appDrawerSearchInput').trigger('input');
            var lastactionID = false;
            var lastmenuactionID = false;
            var lastmenuID = false;
            var lastrecordID = false;
            var lastMenu = false;

    

            _.each(this._appsMenu._apps, function(value) {
                $('a[data-menu-id=' + value.menuID + ']').addClass('d-none');
            });
            
            if (window.location.href.includes('#action=') && !$(event.target).hasClass('parent_menu_option')) {
                var substring = window.location.href.split('#action=');
                if (substring.length && substring.length >= 1) {
                    let previous_action = substring[1].split('&');
                    let previous_record = substring[1].split('id=');

                    let previous_record1 = substring[1].split('hashcode=');

                    if (previous_action.length && previous_action.length >= 1) {
                        lastactionID = parseInt(previous_action[0]);
                    }
                    if (previous_record.length && previous_record.length >= 1) {
                        if(previous_record[1]){
                            let previous_record_id = previous_record[1].split('&');
                            if (previous_record_id.length && previous_record_id.length >= 1) {
                                this.lastrecordID = previous_record_id[0];
                            }
                        }
                    }

                    if (previous_record1.length && previous_record1.length >= 1) {
                        if(previous_record1[1]){
                            let previous_record_id1 = previous_record1[1].split('&');
                            if (previous_record_id1.length && previous_record_id1.length >= 1) {
                                previous_record_id1[0] = previous_record_id1[0].replace('!','=')
                                previous_record_id1[0] = atob(decodeURIComponent(previous_record_id1[0]))
                                this.lastrecordID = previous_record_id1[0];
                            }
                        }
                    }
                }
            }
            else if (window.location.href.includes('&menu_id=')){
                var substring = window.location.href.split('&menu_id=');
                if (substring.length && substring.length >= 1 && window.location.href.split('&menu_id=')[1] != "") {
                    const menu = $("a[data-menu-id='" + window.location.href.split('&menu_id=')[1] + "']");
                    
                    lastactionID = menu.data("action-id");
                }
            }
            if (!lastactionID && !window.location.href.includes('#action=') && !this.autoCompleteChange) {
                if ($('.parent_menu_select option').length) {
                    var first_option = $($('.parent_menu_select option')[0]);
                    first_option.attr('selected', 'selected');
                    var actionID = first_option.data('action-id');
                    var menuID = first_option.data('menu-id');
                    const menu = $('a[data-menu-id=' + menuID + ']');
                    menu.click();
                }
            }
            if (lastactionID && !this.autoCompleteChange) {
                lastMenu = $('a[data-action-id=' + lastactionID + ']');
                lastmenuactionID = lastMenu.data('action-id');
                lastmenuID = lastMenu.data('menu-id');
                if (!lastMenu.hasClass('direct_menu')) {
                    var parent_menu = lastMenu.parents('.cssmenu').find('.o_app2');
                    $('.parent_menu_select').find("option:selected").removeAttr("selected");
                    $('.parent_menu_select option[data-menu-id='+ parent_menu.data('menu-id') +']').attr('selected', 'selected');
                }
                else if (lastMenu.hasClass('direct_menu')) {
                    $('.parent_menu_select').find("option:selected").removeAttr("selected");
                    $('.parent_menu_select option[data-menu-id='+ lastMenu.data('menu-id') +']').attr('selected', 'selected');
                }
            }
            if (window.location.href.includes('&menu_id=') && !this.autoCompleteChange) {
                var substring = window.location.href.split('&menu_id=');
                if (substring.length && substring.length >= 1) { 
                    var Menu = parseInt(substring[1]);
                    if (!isNaN(Menu)) {
                        const menu = $('a[data-menu-id=' + Menu + ']');
                        if (menu.hasClass('action_menu')) {
                            var option_menu = menu.parents('.cssmenu').find('.o_app2');
                            $('.parent_menu_select option[data-menu-id='+ option_menu.data('menu-id') +']').attr('selected', 'selected');
                            var currentMenu = option_menu;
                        }
                        else if (menu.hasClass('o_app2')) {
                            var option_menu = menu;
                            $('.parent_menu_select option[data-menu-id='+ option_menu.data('menu-id') +']').attr('selected', 'selected');
                            var currentMenu = option_menu;
                        }
                        else {
                            var option_menu = $('.parent_menu_select option[data-menu-id='+ menu.data('parent-menu-id') +']');
                            option_menu.attr('selected', 'selected');
                            var currentMenu = option_menu;
                        }
                    }
                    else {
                        var currentMenu = $('.parent_menu_select').find("option:selected");
                    }
                }
                else {
                    var currentMenu = $('.parent_menu_select').find("option:selected");
                }
            }
            else {
                var currentMenu = $('.parent_menu_select').find("option:selected");
            }
            if (window.location.href.includes('&xml_id=')) {
                var substring = window.location.href.split('&xml_id=');
                if (substring.length && substring.length >= 1) {
                    var xml_id = substring[1];
                    var currentMenu = $('a[data-menu-xmlid="' + window.location.href.split('&xml_id=')[1] + '"]').closest('.cssmenu').find('.o_app2');
                    this.currentMenu = $('a[data-menu-xmlid="' + window.location.href.split('&xml_id=')[1] + '"]');
                }
            }
            var actionID = currentMenu.data('action-id');
            var menuID = currentMenu.data('menu-id');
            const menu = $('a[data-menu-id=' + menuID + ']');
            if (this.currentMenu) {
                $('a[data-menu-id=' + this.currentMenu.data('menu-id') + ']').click();
                this.currentMenu.click();
                if (!$(event.target).hasClass('parent_menu_option')) {
                    var actionID = this.currentMenu.data('action-id');
                    var menuID = this.currentMenu.data('menu-id');
                }
            }
            if (window.location.href.includes('#action=') || 
                window.location.href.includes('&menu_id=')) {
                menu.click();
            }
            var app = _.findWhere(this._appsMenu._apps, { actionID: actionID, menuID: menuID });
            if(window.location.href.includes('model=')&&(window.location.href.includes('&id=') || window.location.href.includes('&hashcode='))&&!window.location.href.includes('action=')){
                // Auto direct link, ex: link from email
            }
            else{
                if (app && app.name === "Discuss") {
                    this._trigger_menu_clicked(app.menuID, app.actionID);
                }
                else {
                    if (lastmenuID && lastmenuactionID && 
                        (event.originalEvent === undefined || 
                        lastMenu.hasClass('action_menu')
                        )) {
                        this._trigger_menu_clicked(lastmenuID, lastmenuactionID);
                        $(lastMenu).addClass('active');
                    }
                    else if (app !== undefined &&
                        app.children !== undefined &&
                        app.children.length && (event.originalEvent !== undefined || 
                        event.isTrigger)) {
                        if (menu.next().hasClass('show_ul')) {
                            var child_app = menu.next().find('.action_menu')[0];
                            var childactionID = $(child_app).data('action-id');
                            var childmenuID = $(child_app).data('menu-id');
                            this._trigger_menu_clicked(childmenuID, childactionID);
                            $(child_app).addClass('active');
                        }
                    }
                }
            }
            if (menu.hasClass('child_app')) {
                menu.addClass('d-none');
            }
            if (menu.hasClass('direct_menu')) {
                menu.removeClass('d-none');
            }
            this.currentMenu = currentMenu;
            session.lastmenuId = menuID;
            var xml_id = this.currentMenu.data('menu-xmlid');
            var img = $('a[data-menu-xmlid="' + xml_id + '"]').find('img')
            if (img.length) {
                var new_img = img.clone();
                $('.parent_menu_image').remove();
                new_img.addClass('parent_menu_image');
                new_img.insertBefore($('.parent_menu_autocomplete_dropdown'));
            }
            else if (img.length == 0 && $('.parent_menu_image').length) {
                $('.parent_menu_image').remove();
            }
            var text_length = currentMenu.text().trim().length;
            var space_count = currentMenu.text().trim().split(" ").length - 1;
            var final_length = text_length + space_count;
            if ($('.parent_menu_autocomplete').val() == '') {
                $('.parent_menu_autocomplete').val(currentMenu.text().trim());
            }
        },

        _onMenuitemClick: function(event) {
            var self = this;
            if (event.originalEvent !== undefined) {
                var actionID = $(event.target).closest('.action_menu').data('action-id');
                var menuID = $(event.target).closest('.action_menu').data('menu-id');
                var menus = $('a[data-action-id="' + actionID + '"]:not(.search_menu)');
                if (!menus.hasClass('direct_menu')) {
                    var parent_menu = menus.parents('.cssmenu').find('.o_app2');
                }
                else {
                    var parent_menu = menus;
                }
                if ($(event.target).closest('.action_menu').hasClass('search_menu') && parent_menu.length) {
                    parent_menu = $(parent_menu[0]);
                    $('.parent_menu_select option[data-menu-id='+ parent_menu.data('menu-id') +']').prop('selected', true);
                    $('.parent_menu_select').find("option:selected").removeAttr("selected");
                    $('.parent_menu_autocomplete').val(parent_menu.find('span').text().trim());
                    $('.parent_menu_option').trigger('change');
                    if ($('.parent_menu_image').length == 0) {
                        $("<img src=/web/image?model=ir.ui.menu&amp;field=web_icon_data&amp;id="+parent_menu.data('menu-id')+" class='img sh_standard_icon menu_image parent_menu_image'>").insertBefore($('.parent_menu_autocomplete_dropdown'));
                    }
                    setTimeout(function () {
                        self._trigger_menu_clicked(menuID, actionID);
                        const menu = $('a[data-menu-id=' + menuID + ']');
                        menu.addClass('active');
                    }, 1500);
                }
                else {
                    return self._trigger_menu_clicked(menuID, actionID);
                }
            }
        }
    });
    return Menu;
});