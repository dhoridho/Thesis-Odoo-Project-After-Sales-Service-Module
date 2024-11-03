# -*- coding: utf-8 -*-

template = """{
    "name": "style1",
    "is_default": false,
    "groups": [{
        "name": "side bar",
        "sub_groups": [{
            "name": "app tab",
            "style_items": [{
                "name": "background",
                "selectors": [".navigation .navigation-menu-tab"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$dark_background_color",
                    "identity": "side_bar_background"
                }],
                "val_template": "background: {color} !important;"
            }, {
                "name": "text color",
                "selectors": [".navigation .side_bar .navigation-menu-tab .app_name"],
                "val_template": "color: {color} !important;",
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$text_color"
                }]
            }]
        }, {
            "name": "footer",
            "style_items": [{
                "name": "background",
                "selectors": [".navigation .awesome-nav-footer"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$light_background_color",
                    "identity": "footer_background"
                }],
                "val_template": "background: {color} !important;"
            }]
        }, {
            "name": "sub menu",
            "style_items": [{
                "name": "background",
                "selectors": [".navigation .navigation-menu-body"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$dark_background_color"
                }],
                "val_template": "background-color: {color} !important;"
            }, {
                "name": "menu board border color",
                "selectors": [".navigation .navigation-menu-body"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$border_color"
                }],
                "val_template": "border-right-color: {color} !important;"
            }, {
                "name": "menu item active color",
                "selectors": [".navigation ul li > a.active"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$menu_item_hover_color"
                }],
                "val_template": "background-color: {color} !important;"
            }, {
                "name": "indicator color",
                "selectors": [".navigation ul li > a.active:after"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$primary_color"
                }],
                "val_template": "background-color: {color} !important;"
            }, {
                "name": "active text color",
                "selectors": [".navigation ul li > a.active"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$link_active_color"
                }],
                "val_template": "color: {color} !important;"
            }]
        }]
    }, {
        "name": "app board",
        "sub_groups": [{
            "name": "normal",
            "style_items": [{
                "name": "background",
                "selectors": [".menu_board .board-pannel"],
                "vars": [{
                    "type": "color",
                    "name": "color1",
                    "color": "$dark_background_color"
                }, {
                    "type": "color",
                    "name": "color2",
                    "color": "$light_background_color"
                }],
                "val_template": "background: radial-gradient({color1}, {color2}) !important;"
            }]
        }]
    }, {
        "name": "header",
        "sub_groups": [{
            "name": "normal",
            "style_items": [{
                "name": "background",
                "selectors": [".header"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$dark_background_color",
                    "identity": "header_background"
                }],
                "val_template": "background-color: {color} !important;"
            }]
        }, {
            "name": "toggler",
            "style_items": [{
                "name": "background",
                "selectors": [".header .navigation-toggler a"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$primary_color"
                }],
                "val_template": "background-color: {color} !important;"
            },  {
                "name": "border color",
                "selectors": [".header .navigation-toggler"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$primary_border_color"
                }],
                "val_template": "border-color: {color} !important;"
            }, {
                "name": "hover background",
                "selectors": [".header .navigation-toggler:hover"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$menu_item_hover_color"
                }],
                "val_template": "background-color: {color} !important;"
            }]
        }, {
            "name": "search bar",
            "style_items": [{
                "name": "background",
                "selectors": [".theme_header .search_bar .o_searchview"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$dark_background_color"
                }],
                "val_template": "background-color: {color} !important;"
            }, {
                "name": "input background",
                "selectors": [
                    ".theme_header .search_bar  .o_searchview",
                    ".theme_header .search_bar .o_searchview .o_searchview_input"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$dark_background_color"
                }],
                "val_template": "background-color: {color} !important;"
            }, {
                "name": "border",
                "selectors": [".theme_header .search_bar .o_searchview"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$dark_border_color"
                }],
                "val_template": "border-color: {color} !important;"
            }, {
                "name": "text color",
                "selectors": [".theme_header .search_bar .o_searchview",
                              ".theme_header .search_bar .o_searchview input"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$text_color"
                }],
                "val_template": "color: {color} !important;"
            }, {
                "name": "dropdown hover color",
                "selectors": [
                    ".theme_header .search_bar .dropdown-menu .dropdown-item:hover"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$menu_item_hover_color"
                }],
                "val_template": "color: {color} !important;"
            }, {
                "name": "button background",
                "selectors": [".theme_header .search_bar .o_dropdown > button"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$primary_color"
                }],
                "val_template": "background-color: {color} !important;"
            }, {
                "name": "hover background",
                "selectors": [".theme_header .search_bar .o_dropdown > button:hover"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$menu_item_hover_color"
                }],
                "val_template": "background-color: {color} !important;"
            }, {
                "name": "dropdown background color",
                "selectors": [".theme_header .search_bar .dropdown-menu"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$dark_background_color"
                }],
                "val_template": "background-color: {color} !important;"
            }]
        }]
    }, {
        "name": "body",
        "sub_groups": [{
            "name": "normal",
            "style_items": [{
                "name": "background",
                "sub_group": "body",
                "selectors": ["body", ".o_action_manager"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$dark_background_color"
                }],
                "val_template": "background-color: {color} !important;"
            }]
        }]
    }, {
        "name": "footer",
        "sub_groups": [{
            "name": "normal",
            "style_items": [{
                "name": "background color",
                "selectors": [".footer"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$dark_background_color"
                }],
                "val_template": "background-color: {color} !important;"
            }, {
                "name": "border color",
                "selectors": [".footer"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$border_color"
                }],
                "val_template": "border-color: {color} !important;"
            }]
        }]
    }, {
        "name": "primary button",
        "sub_groups": [{
            "name": "normal",
            "style_items": [{
                "name": "background",
                "selectors": [".btn-primary"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$primary_color"
                }],
                "val_template": "background-color: {color} !important;"
            }, {
                "name": "text",
                "selectors": [".btn-primary"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$primary_text_color"
                }],
                "val_template": "color: {color} !important;"
            }, {
                "name": "hover",
                "selectors": [".btn-primary:hover"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$primary_hover_color"
                }],
                "val_template": "background-color: {color} !important;"
            }, {
                "name": "border color",
                "selectors": [".btn-primary:hover"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$primary_border_color"
                }],
                "val_template": "border-color: {color} !important;"
            }, {
                "name": "hover border color",
                "selectors": [".btn-primary:hover"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$primary_border_hover_color"
                }],
                "val_template": "border-color: {color} !important;"
            }, {
                "name": "hover text color",
                "selectors": [".btn-primary:hover"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$primary_text_hover_color"
                }],
                "val_template": "color: {color} !important;"
            }]
        }]
    }, {
        "name": "secondary button",
        "sub_groups": [{
            "name": "normal",
            "style_items": [{
                "name": "background color",
                "selectors": [".btn-secondary"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$secondary_color"
                }],
                "val_template": "background-color: {color} !important;"
            }, {
                "name": "border color",
                "selectors": [".btn-secondary"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$secondary_border_color"
                }],
                "val_template": "border-color: {color} !important;"
            }, {
                "name": "text color",
                "selectors": [".btn-secondary"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$secondary_text_color"
                }],
                "val_template": "color: {color} !important;"
            }, {
                "name": "hover background",
                "selectors": [".btn-secondary:hover"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$secondary_hover_color"
                }],
                "val_template": "background-color: {color} !important;"
            }, {
                "name": "hover border color",
                "selectors": [".btn-secondary:hover"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$secondary_border_hover_color"
                }],
                "val_template": "border-color: {color} !important;"
            }, {
                "name": "hover text color",
                "selectors": [".btn-secondary:hover"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$secondary_text_hover_color"
                }],
                "val_template": "color: {color} !important;"
            }]
        }]
    }, {
        "name": "control panel",
        "sub_groups": [{
            "name": "normal",
            "style_items": [{
                "name": "background color",
                "selectors": [".o_control_panel"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$light_background_color"
                }],
                "val_template": "background-color: {color} !important;"
            }]
        }, {
            "name": "breadcrumb",
            "style_items": [{
                "name": "text color",
                "selectors": [".breadcrumb-item"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$link_text_color"
                }],
                "val_template": "color: {color} !important;"
            }, {
                "name": "active text color",
                "selectors": [".breadcrumb-item.active"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$link_text_active_color"
                }],
                "val_template": "color: {color} !important;"
            }]
        }]
    }, {
        "name": "list view",
        "sub_groups": [{
            "name": "header",
            "style_items": [{
                "name": "text color",
                "selectors": [".o_list_view .o_list_table thead"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$dark_background_color"
                }],
                "val_template": "color: {color} !important;"
            }, {
                "name": "background",
                "selectors": [".o_list_view .table-responsive .o_list_table thead",
                              ".o_list_view .table-responsive .o_list_table thead tr:nth-child(1) th"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$dark_background_color"
                }],
                "val_template": "background-color: {color} !important;"
            }]
        }, {
            "name": "body",
            "style_items": [{
                "name": "text color",
                "selectors": [".o_list_view .o_list_table"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$table_text_color"
                }],
                "val_template": "color: {color} !important;"
            }, {
                "name": "row hover color",
                "selectors": [".table-hover tbody tr:hover"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$table_row_hover_color"
                }],
                "val_template": "background-color: {color} !important;"
            }, {
                "name": "odd row color",
                "selectors": [".table-striped tbody tr:nth-of-type(odd)"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$table_even_row_color"
                }],
                "val_template": "background-color: {color} !important;"
            }]
        }, {
            "name": "footer",
            "style_items": [{
                "name": "background",
                "selectors": [".o_list_view .table-responsive .o_list_table tfoot",
                              ".o_list_view .table-responsive .o_list_table tfoot tr:nth-child(1) td "],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "$light_background_color"
                }],
                "val_template": "background-color: {color} !important;"
            }]
        }]
    }]
}"""

