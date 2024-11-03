odoo.define('awesome_theme_pro.multi_tab_page', function (require) {
    "use strict";

    const Widget = require('web.Widget');
    const core = require('web.core')

    // just require it
    require('web.ActWindowActionManager')

    var MultiTabWidget = Widget.extend({

        template: 'awesome_theme_pro.multi_tab',
        actions: [],

        events: _.extend({}, Widget.prototype.events, {
            "click .awesome_page_tab_item": '_on_click_tab_item',
            "click .awesome_tab_close": '_on_click_tab_close',
            "click .awesome_icon_prev": "_on_multi_tab_prev",
            "click .awesome_icon_next": "_on_multi_tab_next",
            "click .awesome_close_cur_tab": "_on_close_cur_tab",
            "click .awesome_close_other_tabs": "_on_close_other_tabs",
            "click .awesome_close_all_tabs": "_on_close_all_tabs"
        }),

        start: function (parent) {
            this._super.apply(this, arguments);
        },

        willStart: function () {
            return this._super.apply(this, arguments);
        },

        /**
         * maybe there is some thing wrong! need full test
         * @param {*} action 
         * @param {*} options 
         */
        /**
         * maybe there is some thing wrong! need full test
         * @param {*} action 
         * @param {*} options 
         */
         get_action_info: function (action, options) {
            var old_action = _.find(this.actions, function (action_info) {
                var tmp_action = action_info.action
                // clone context to prevent it
                var tmp_context1 = _.clone(tmp_action.context)
                var tmp_context2 = _.clone(action.context)
                if (!tmp_context2.params) {
                    tmp_context2.params = {}
                } else {
                    delete tmp_context2.params['action']
                    delete tmp_context2.params['cids']
                    delete tmp_context2.params['model']
                    delete tmp_context2.params['view_type']
                    delete tmp_context2.params['menu_id']
                }
                // ignore the action related params
                if (tmp_context1.params) {
                    delete tmp_context1.params['action']
                    delete tmp_context1.params['cids']
                    delete tmp_context1.params['model']
                    delete tmp_context1.params['view_type']
                    delete tmp_context1.params['menu_id']
                } else {
                    tmp_context1.params = {}
                }

                if (tmp_action.id == action.id
                    && tmp_action.name == action.name
                    && tmp_action.xml_id == action.xml_id
                    && tmp_action.view_mode == action.view_mode
                    && tmp_action.binding_model_id == action.binding_model_id
                    && tmp_action.binding_type == action.binding_type
                    && tmp_action.binding_view_types == action.binding_view_types
                    && tmp_action.res_id == action.res_id
                    && JSON.stringify(tmp_action.domain) == JSON.stringify(action.domain)
                    && _.isEqual(tmp_context1, tmp_context2)) {
                    return true
                } else {
                    return false
                }
            })
            return old_action
        },

        is_action_exists: function (action, options) {
            var old_action = this.get_action_info(action, options)
            return old_action ? true : false;
        },

        /**
         * @param {*} action 
         * @param {*} options 
         */
        on_excute_action: function (action, options) {
            var old_action = this.get_action_info(action, options)
            if (old_action) {
                this.active_tab(old_action.jsID);
            } else {
                this._deactive_all_tab();
                var $cur_tab_item = this._add_action_item(action);
                // make it action
                $cur_tab_item.addClass('awesome_multi_tab_active');
                this.actions.push({
                    "jsID": action.jsID,
                    "action": action,
                    "options": options
                })
                var index = this._get_tab_index($cur_tab_item);
                this.rollPage('auto', index);
            }
        },

        _deactive_all_tab: function (jsID) {
            this.$('.awesome_page_tab_item').removeClass('awesome_multi_tab_active');
        },

        active_tab: function (jsID) {
            this._deactive_all_tab();
            var $cur_action_item = this.$('.awesome_page_tab_item[data-action-id=' + jsID + ' ]');
            $cur_action_item.addClass('awesome_multi_tab_active');
            return $cur_action_item;
        },

        /**
         * close action tab
         */
        _on_click_tab_close: function (event) {

            event.preventDefault()
            event.stopPropagation();

            // notify remove action
            var $target = $(event.currentTarget)

            var $tab_item = $target.parent()
            var index = this._get_tab_index($tab_item)

            var action_id = $tab_item.data('action-id')
            var action_info = this._get_action(action_id)

            var self = this;

            this.trigger_up('awesome_remove_action', {

                action: action_info.action,
                options: action_info.options,

                call_back: function () {

                    $tab_item.remove()

                    // remove the action from the list
                    self._remove_action(action_id)

                    if (self.actions.length == 0) {
                        return;
                    }

                    // execute the action
                    index -= 1
                    if (index < 0)
                        index = self.actions.length - 1;

                    var new_action = self.actions[index];

                    // active the prev one
                    self.trigger_up('awesome_tab_restore_action', { action: new_action.action, options: new_action.options })

                    // active the tab item
                    self.active_tab(new_action.jsID);

                    self.rollPage('auto', index);
                }
            });
        },

        _remove_action: function (jsID) {
            var index = _.findIndex(this.actions, function (action_info) {
                return action_info.action.jsID == jsID
            })
            if (index != -1) {
                this.actions.splice(index, 1)
            }
        },

        _get_action: function (action_id) {
            var action = _.find(this.actions, function (tmp_action) {
                return tmp_action.jsID == action_id;
            })
            return action;
        },

        _remove_action_item: function (jsID) {
            var $actionItem = this.$('.awesome_tab_item[action_id=' + jsID + ']');
            $actionItem.remove();
        },

        _add_action_item: function (action) {
            var $newItem = $(core.qweb.render('awesome_theme_pro.multi_tab_page_item', {
                action: action
            }));
            $newItem.appendTo(this.$('.tab_container'));
            return $newItem;
        },

        _get_tab_index: function (tab_item) {
            var index = this.$('.awesome_page_tab_item').index(tab_item)
            return index;
        },

        _get_curactive_tab: function () {
            var active_item = this.$('.awesome_multi_tab_active')
            if (active_item) {
                return this._get_tab_index(active_item);
            } else {
                // return the last item`
                return this.actions.length - 1;
            }
        },

        _on_multi_tab_prev: function () {
            if (this.actions.length == 0) {
                return;
            }

            var index = this._get_curactive_tab();
            index = index - 1;
            if (index < 0) {
                if (this.actions.length > 0) {
                    index = this.actions.length - 1;
                } else {
                    return;
                }
            }

            var $tab_item = this.$('.awesome_page_tab_item').eq(index);
            $tab_item.click()
        },

        _on_multi_tab_next: function () {

            if (this.actions.length == 0) {
                return;
            }

            var index = this._get_curactive_tab();
            index = index + 1;
            if (index >= this.actions.length) {
                index = 0;
            }

            var $tab_item = this.$('.awesome_page_tab_item').eq(index);
            $tab_item.click()
        },

        /**
         * click tab item
         */
        _on_click_tab_item: function (ev) {
            ev.preventDefault();
            var $target = $(ev.currentTarget)
            var action_id = $target.data('action-id')
            var action_info = _.find(this.actions, function (tmp_action) {
                return tmp_action.jsID == action_id;
            })
            // active the tab
            this.active_tab(action_info.action.jsID);
            this.trigger_up('awesome_tab_restore_action', { action: action_info.action, options: action_info.options })

            var index = this._get_tab_index($target);
            this.rollPage('auto', index);
        },

        /**
         * close current tab
         * @param {*} event 
         */
        _on_close_cur_tab: function (event) {
            event.preventDefault();

            var index = this._get_curactive_tab();
            var $tab_items = this.$('.awesome_page_tab_item').eq(index)
            $tab_items.find('.awesome_tab_close').click()
        },

        /**
         * close other tabs
         * @param {*} event 
         */
        _on_close_other_tabs: function (event) {
            event.preventDefault();

            var self = this;
            var index = this._get_curactive_tab();
            var $tab_items = this.$('.awesome_page_tab_item').not(":eq(" + index + ")")
            _.each($tab_items, function (item, index) {

                var $tab_item = $(item);
                var action_id = $tab_item.data('action-id')
                var action_info = self._get_action(action_id)

                self.trigger_up('awesome_remove_action', {
                    action: action_info.action, options: action_info.options, call_back: function () {
                        $tab_item.remove()
                        self._remove_action(action_id)
                    }
                });
            })
        },

        /**
         * close all tabs
         * @param {*} event 
         */
        _on_close_all_tabs: function (event) {
            event.preventDefault();

            var self = this;
            var $tab_items = this.$('.awesome_page_tab_item')
            _.each($tab_items, function (item, index) {

                var $tab_item = $(item);
                var action_id = $tab_item.data('action-id')
                var action_info = self._get_action(action_id)

                self.trigger_up('awesome_remove_action', {
                    action: action_info.action, options: action_info.options, call_back: function () {
                        $tab_item.remove()
                        self._remove_action(action_id)
                    }
                });
            })
        },

        /**
         * roll page
         * @param {*} type 
         * @param {*} index 
         */
        rollPage: function (type, index) {

            var tabsHeader = this.$('.awesome_page_items')
            var li_items = tabsHeader.children('li')
            var outerWidth = tabsHeader.outerWidth()
            var tabsLeft = parseFloat(tabsHeader.css('left'));

            if (type === 'left') {
                if (!tabsLeft && tabsLeft <= 0) {
                    return;
                }
                var prefLeft = -tabsLeft - outerWidth;
                li_items.each(function (index, item) {
                    var li = $(item)
                    var left = li.position().left;

                    if (left >= prefLeft) {
                        tabsHeader.css('left', -left);
                        return false;
                    }
                });
            } else if (type === 'auto') {
                var thisLi = li_items.eq(index)
                if (!thisLi[0]) {
                    return
                };
                var thisLeft = thisLi.position().left;
                if (thisLeft < -tabsLeft) {
                    return tabsHeader.css('left', -thisLeft);
                }
                if (thisLeft + thisLi.outerWidth() >= outerWidth - tabsLeft) {
                    var subLeft = thisLeft + thisLi.outerWidth() - (outerWidth - tabsLeft);
                    li_items.each(function (i, item) {
                        var li = $(item)
                        var left = li.position().left;
                        if (left + tabsLeft > 0) {
                            if (left - tabsLeft > subLeft) {
                                tabsHeader.css('left', -left);
                                return false;
                            }
                        }
                    });
                }
            } else {
                li_items.each(function (i, item) {
                    var li = $(item)
                    var left = li.position().left;

                    if (left + li.outerWidth() >= outerWidth - tabsLeft) {
                        tabsHeader.css('left', -left);
                        return false;
                    }
                });
            }
        }
    });

    return MultiTabWidget;
});
