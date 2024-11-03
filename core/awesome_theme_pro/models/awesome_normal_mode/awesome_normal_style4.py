# -*- coding: utf-8 -*-

normal_style4 = {
    "name": "normal style4",
    "is_default": True,
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
                    "color": "#1565c0",
                    "identity": "side_bar_background",
                }],
                "val_template": "background: {color} !important;",
            }, {
                "name": "text color",
                "selectors": [".navigation .side_bar .navigation-menu-tab .awesome_app_name"],
                "val_template": "color: {color} !important;",
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#fff",
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
                    "color": "#12549e",
                    "identity": "footer_background",
                }],
                "val_template": "background: {color} !important;",
            }]
        }, {
            "name": "sub menu",
            "style_items": [{
                "name": "background",
                "selectors": [".navigation .navigation-menu-body"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#fff",
                }],
                "val_template": "background-color: {color} !important;",
            }, {
                "name": "menu board border color",
                "selectors": [".navigation .navigation-menu-body"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#ebebeb",
                }],
                "val_template": "border-right-color: {color} !important;",
            }, {
                "name": "menu item color",
                "selectors": [".navigation ul li > a"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#505050",
                }],
                "val_template": "color: {color} !important;"
            }, {
                "name": "menu item active color",
                "selectors": [".navigation ul li > a.active"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#eee",
                }],
                "val_template": "background-color: {color} !important;"
            }, {
                "name": "indicator color",
                "selectors": [".navigation ul li > a.active:after"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#1565c0",
                }],
                "val_template": "background-color: {color} !important;"
            }, {
                "name": "active text color",
                "selectors": [".navigation ul li > a.active"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#1565c0",
                }],
                "val_template": "color: {color} !important;",
            }]
        }]
    }, {
        "name": "app board",
        "sub_groups": [{
            "name": "normal",
            "style_items": [{
                "name": "background",
                "selectors": [".awesome_menu_board .board-pannel"],
                "vars": [{
                    "type": "color",
                    "name": "color1",
                    "color": "#1565c0"
                }, {
                    "type": "color",
                    "name": "color1",
                    "color": "#070729"
                }],
                "val_template": "background: radial-gradient({color1}, {color2}) !important;",
            }]
        }, {
            "name": "search",
            "style_items": [{
                "name": "background",
                "selectors": [".board-pannel .search_bar .search_box",
                              ".board-pannel .search_bar .search_box .search_input"],
                "vars": [{
                    "type": "color",
                    "name": "color1",
                    "color": "#1565c0"
                }],
                "val_template": "background: {color1} !important;",
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
                    "color": "#fff",
                    "identity": "header_background",
                }],
                "val_template": "background-color: {color} !important;",
            }]
        }, {
            "name": "toggler",
            "style_items": [{
                "name": "background",
                "selectors": [".header .navigation-toggler a"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#fff"
                }],
                "val_template": "background-color: {color} !important;",
            }, {
                "name": "hover background",
                "selectors": [".header .navigation-toggler a:hover"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#ececec"
                }],
                "val_template": "background-color: {color} !important;",
            }, {
                "name": "border color",
                "selectors": [".header .navigation-toggler"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#e6e5e5"
                }],
                "val_template": "border-color: {color} !important;",
            }, {
                "name": "hover background",
                "selectors": [".header .navigation-toggler:hover"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#3b425c"
                }],
                "val_template": "background-color: {color} !important;"
            }]
        }, {
            "name": "search bar",
            "style_items": [{
                "name": "background",
                "selectors": [".awesome_theme_header .awesome_search_bar .o_searchview"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#fff"
                }],
                "val_template": "background-color: {color} !important;",
            }, {
                "name": "input background",
                "selectors": [
                    ".awesome_theme_header .awesome_search_bar  .o_searchview",
                    ".awesome_theme_header .awesome_search_bar .o_searchview .o_searchview_input"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#fff"
                }],
                "val_template": "background-color: {color} !important;"
            }, {
                "name": "border",
                "selectors": [".awesome_theme_header .awesome_search_bar .o_searchview"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#ccc"
                }],
                "val_template": "border-color: {color} !important;"
            }, {
                "name": "text color",
                "selectors": [".awesome_theme_header .awesome_search_bar .o_searchview",
                              ".awesome_theme_header .awesome_search_bar .o_searchview input"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#4c4c4c"
                }],
                "val_template": "color: {color} !important;"
            }, {
                "name": "dropdown hover color",
                "selectors": [
                    ".awesome_theme_header .awesome_search_bar .dropdown-menu .dropdown-item:hover"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#6b69b5"
                }],
                "val_template": "color: {color} !important;",
            }, {
                "name": "background",
                "selectors": [".awesome_theme_header .awesome_search_bar .o_dropdown > button"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#fff"
                }],
                "val_template": "background-color: {color} !important;"
            }, {
                "name": "hover background",
                "selectors": [".awesome_theme_header .awesome_search_bar .o_dropdown > button:hover"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#e6e5e5"
                }],
                "val_template": "background-color: {color} !important;"
            }, {
                "name": "dropdown background color",
                "selectors": [".awesome_theme_header .awesome_search_bar .dropdown-menu"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#fff"
                }],
                "val_template": "background-color: {color} !important;",
            }, {
                "name": "dropdown text color",
                "selectors": [".awesome_theme_header .awesome_search_bar .dropdown-menu .menuitem a"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#333232"
                }],
                "val_template": "background-color: {color} !important;",
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
                    "color": "#f9f9f9",
                    "identity": "body_background",
                }],
                "val_template": "background-color: {color} !important;",
            }]
        }]
    }, {
        "name": "footer",
        "sub_groups": [{
            "name": "normal",
            "style_items": [{
                "name": "background color",
                "selectors": [".awesome_footer"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#fff"
                }],
                "val_template": "background-color: {color} !important;",
            }, {
                "name": "border color",
                "selectors": [".awesome_footer"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#dee2e6"
                }],
                "val_template": "border-color: {color} !important;",
            }, {
                "name": "text color",
                "sub_group": "normal",
                "selectors": [".awesome_footer a"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#6c757d"
                }],
                "val_template": "color: {color} !important;",
            }],
        }, {
            "name": "pager",
            "style_items": [{
                "name": "color",
                "sub_group": "button",
                "selectors": [".awesome_footer .o_pager button"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#fff"
                }],
                "val_template": "background-color: {color} !important;",
            }, {
                "name": "active background color",
                "sub_group": "button",
                "selectors": [".awesome_footer .o_pager button:hover"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#ececec"
                }],
                "val_template": "background-color: {color} !important;",
            }, {
                "name": "hover color",
                "sub_group": "button",
                "selectors": [".awesome_footer .o_pager button:hover"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#212529"
                }],
                "val_template": "color: {color} !important;",
            }, {
                "name": "active border color",
                "sub_group": "button",
                "selectors": [".awesome_footer .o_pager button:hover"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#e6e5e5"
                }],
                "val_template": "border-color: {color} !important;",
            }],
        }, {
            "name": "switcher",
            "style_items": [{
                "name": "switcher button background color",
                "selectors": [".awesome_footer .o_cp_switch_buttons button"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#fff"
                }],
                "val_template": "background-color: {color} !important;",
            }, {
                "name": "border color",
                "selectors": [".awesome_footer .o_cp_switch_buttons button"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#dee2e6"
                }],
                "val_template": "border-color: {color} !important;",
            }, {
                "name": "active text color",
                "selectors": [".awesome_footer .o_cp_switch_buttons button.active"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#212529"
                }],
                "val_template": "color: {color} !important;",
            }, {
                "name": "active background color",
                "selectors": [".awesome_footer .o_cp_switch_buttons button.active"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#e6e5e5"
                }],
                "val_template": "background-color: {color} !important;",
            }, {
                "name": "active border color",
                "selectors": [".awesome_footer .o_cp_switch_buttons button.active"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#dfdfdf"
                }],
                "val_template": "border-color: {color} !important;",
            }, {
                "name": "hover background color",
                "selectors": [".awesome_footer .o_cp_switch_buttons button:hover"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#ececec"
                }],
                "val_template": "background-color: {color} !important;",
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
                    "color": "#007bff"
                }],
                "val_template": "background-color: {color} !important;",
            }, {
                "name": "text",
                "selectors": [".btn-primary"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#fff"
                }],
                "val_template": "color: {color} !important;",
            }, {
                "name": "hover",
                "selectors": [".btn-primary:hover"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#006fe6"
                }],
                "val_template": "background-color: {color} !important;",
            }, {
                "name": "border color",
                "selectors": [".btn-primary:hover"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#007bff"
                }],
                "val_template": "border-color: {color} !important;",
            }, {
                "name": "hover border color",
                "selectors": [".btn-primary:hover"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#006fe6"
                }],
                "val_template": "border-color: {color} !important;",
            }, {
                "name": "hover text color",
                "selectors": [".btn-primary:hover"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#fff"
                }],
                "val_template": "color: {color} !important;",
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
                    "color": "#fff"
                }],
                "val_template": "background-color: {color} !important;",
            }, {
                "name": "border color",
                "selectors": [".btn-secondary"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#e6e5e5"
                }],
                "val_template": "border-color: {color} !important;",
            }, {
                "name": "text color",
                "selectors": [".btn-secondary"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#212529"
                }],
                "val_template": "color: {color} !important;",
            }, {
                "name": "hover background",
                "selectors": [".btn-secondary:hover"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#ececec"
                }],
                "val_template": "background-color: {color} !important;",
            }, {
                "name": "hover border color",
                "selectors": [".btn-secondary:hover"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#e6e5e5"
                }],
                "val_template": "border-color: {color} !important;",
            }, {
                "name": "hover text color",
                "selectors": [".btn-secondary:hover"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#212529"
                }],
                "val_template": "color: {color} !important;",
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
                    "color": "#fff"
                }],
                "val_template": "background-color: {color} !important;",
            }],
        }, {
            "name": "breadcrumb",
            "style_items": [{
                "name": "text color",
                "selectors": [".breadcrumb-item"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#777777"
                }],
                "val_template": "color: {color} !important;",
            }, {
                "name": "active text color",
                "selectors": [".breadcrumb-item.active"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#f6f6f6"
                }],
                "val_template": "color: {color} !important;",
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
                    "color": "#4c4c4c"
                }],
                "val_template": "color: {color} !important;",
            }, {
                "name": "background",
                "selectors": [".o_list_view .table-responsive .o_list_table thead",
                              ".o_list_view .table-responsive .o_list_table thead tr:nth-child(1) th"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#fff"
                }],
                "val_template": "background-color: {color} !important;",
            }],
        }, {
            "name": "body",
            "style_items": [{
                "name": "text color",
                "selectors": [".o_list_view .o_list_table"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "#4c4c4c"
                }],
                "val_template": "color: {color} !important;",
            }, {
                "name": "row hover color",
                "selectors": [".table-hover tbody tr:hover"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "rgba(0, 0, 0, 0.04)"
                }],
                "val_template": "background-color: {color} !important;",
            }, {
                "name": "odd row color",
                "selectors": [".table-striped tbody tr:nth-of-type(odd)"],
                "vars": [{
                    "type": "color",
                    "name": "color",
                    "color": "rgba(0, 0, 0, 0.04)"
                }],
                "val_template": "background-color: {color} !important;",
            }]
        }]
    }]
}
