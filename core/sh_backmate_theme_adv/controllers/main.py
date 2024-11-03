# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo.tools.safe_eval import safe_eval
from odoo import http
from odoo.http import request
import json
from datetime import datetime
from odoo.tools.mimetypes import guess_mimetype
from odoo.modules import get_module_path, get_resource_path
import odoo
import io
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import functools
import base64
db_monodb = http.db_monodb


dict_pre_theme_color_style = {
    'pre_color_1': {
        'theme_color': 'color_1',
        'theme_style': 'style_2',
        'primary_color': '#2C3782',
        'primary_hover': '#2C3782',
        'primary_active': '#2C3782',
        'secondary_color': '#EEEEEE',
        'secondary_hover': '#EEEEEE',
        'secondary_active': '#EEEEEE',
        'header_background_color': '#FFFFFF',
        'body_background_color': '#FFFFFF',
        'header_font_color': '#787373',
        'header_hover_color': '#2C3782',
        'header_active_color': '#2C3782',
        'h1_color': '#464d69',
        'h2_color': '#464d69',
        'h3_color': '#464d69',
        'h4_color': '#464d69',
        'h5_color': '#464d69',
        'h6_color': '#464d69',
        'p_color': '#464d69',
        'h1_size': 28,
        'h2_size': 17,
        'h3_size': 18,
        'h4_size': 13,
        'h5_size': 13,
        'h6_size': 12,
        'p_size': 13,

        'sidebar_is_show_nav_bar': True,
        'sidebar_collapse_style': 'expanded',
        'sidebar_font_hover_background_color': '#2C3782',
        'sidebar_background_style': 'color',
        'sidebar_background_color': '#FFFFFF',
        'sidebar_font_color': '#181F4C',
        'sidebar_font_hover_color': '#FFFFFF',

        'separator_color': '#2C3782',
        'separator_style': 'style_7',

        'button_style': 'style_2',
        'is_button_with_icon_text': True,
        'is_button_with_box_shadow': True,

        'body_background_type': 'bg_color',
        'body_font_color': '#787373',
        'body_font_family': 'Poppins',
        'body_google_font_family': 'Muli',
        'is_used_google_font': False,

        'list_view_border': 'without_border',
        'list_view_is_hover_row': True,
        'list_view_hover_bg_color': '#F2F2F2',
        'list_view_even_row_color': '#ECECEC',
        'list_view_odd_row_color': '#FFFFFF',

        'login_page_style': 'style_2',
        'login_page_background_type': 'bg_color',
        # 'login_page_box_color':False,
        'loading_style': 'style_1',
        'progress_style':'style_1',
        'progress_height':'4px',
        'progress_color': '#2C3782',

        'modal_popup_style': 'style_2',
        'horizontal_tab_style': 'style_5',
        'vertical_tab_style': 'style_5',
        'form_element_style': 'style_1',
        'breadcrumb_style': 'style_1',
        'search_style': 'expanded',
        'chatter_position':'normal'
    },

    'pre_color_2': {
        'theme_color': 'color_7',
        'theme_style': 'style_1',
        'primary_color': '#43A047',
        'primary_hover': '#3B9141',
        'primary_active': '#3B9141',
        'secondary_color': '#EFF2F7',
        'secondary_hover': '#EFF2F7',
        'secondary_active': '#EFF2F7',
        'header_background_color': '#FFFFFF',
        'body_background_color': '#FFFFFF',
        'header_font_color': '#74788D',
        'header_hover_color': '#3B9141',
        'header_active_color': '#3B9141',
        'h1_color': '#495057',
        'h2_color': '#495057',
        'h3_color': '#495057',
        'h4_color': '#495057',
        'h5_color': '#495057',
        'h6_color': '#495057',
        'p_color': '#495057',
        'h1_size': 28,
        'h2_size': 17,
        'h3_size': 18,
        'h4_size': 13,
        'h5_size': 13,
        'h6_size': 12,
        'p_size': 13,

        'sidebar_is_show_nav_bar': True,
        'sidebar_collapse_style': 'collapsed',
        'sidebar_font_hover_background_color': '#FFFFFF',
        'sidebar_background_style': 'color',
        'sidebar_background_color': '#FFFFFF',
        'sidebar_font_color': '#495057',
        'sidebar_font_hover_color': '#495057',

        'separator_color': '#43A047',
        'separator_style': 'style_5',

        'button_style': 'style_4',
        'is_button_with_icon_text': True,
        'is_button_with_box_shadow': True,

        'body_background_type': 'bg_color',
        'body_font_color': '#74788D',
        'body_font_family': 'Poppins',
        'body_google_font_family': 'Muli',
        'is_used_google_font': False,

        'list_view_border': 'without_border',
        'list_view_is_hover_row': True,
        'list_view_hover_bg_color': '#E8F5E9',
        #         'list_view_hover_bg_color':'rgb(232 245 233)',
        'list_view_even_row_color': '#FFFFFF',
        'list_view_odd_row_color': '#FFFFFF',

        'login_page_style': 'style_1',
         'loading_style':'style_4',
         'progress_style':'style_1',
         'progress_height':'4px',
         'progress_color': '#43A047',
        'login_page_background_type': 'bg_color',
        # 'login_page_box_color':False,

        'modal_popup_style': 'style_1',
        'is_sticky_form': True,
        'horizontal_tab_style': 'style_4',
        'vertical_tab_style': 'style_4',
        'form_element_style': 'style_8',
        'breadcrumb_style': 'style_3',
        'search_style': 'collapsed',
        'chatter_position':'normal'
    },


    'pre_color_3': {
        'theme_color': 'color_3',
        'theme_style': 'style_3',
        'primary_color': '#ED4762',
        'primary_hover': '#DD3C54',
        'primary_active': '#DD3C54',
        'gradient_color': '#4F2499',
        'secondary_color': '#EEEEEE',
        'secondary_hover': '#EEEEEE',
        'secondary_active': '#EEEEEE',
        'header_background_color': '#FFFFFF',
        'body_background_color': '#FFFFFF',
        'header_font_color': '#787373',
        'header_hover_color': '#ED4762',
        'header_active_color': '#ED4762',
        'h1_color': '#585858',
        'h2_color': '#585858',
        'h3_color': '#585858',
        'h4_color': '#585858',
        'h5_color': '#585858',
        'h6_color': '#585858',
        'p_color': '#585858',
        'h1_size': 28,
        'h2_size': 17,
        'h3_size': 18,
        'h4_size': 13,
        'h5_size': 13,
        'h6_size': 12,
        'p_size': 13,

        'sidebar_is_show_nav_bar': False,
        'sidebar_collapse_style': 'collapsed',
        'sidebar_background_style': 'image',
        #        'sidebar_font_hover_background_color': '#FFFFFF',
        'sidebar_font_color': '#FFFFFF',
        'sidebar_font_hover_color': '#FFFFFF',
        'sidebar_is_show_nav_bar': False,

        'separator_color': '#ED4762',
        'separator_style': 'style_2',

        'button_style': 'style_5',
        'is_button_with_icon_text': False,
        'is_button_with_box_shadow': True,

        'body_background_type': 'bg_color',
        'body_font_color': '#787373',
        'body_font_family': 'Roboto',
        'body_google_font_family': 'Muli',
        'is_used_google_font': False,

        'list_view_border': 'bordered',
        'list_view_is_hover_row': True,
        'list_view_hover_bg_color': '#FCE4EC',
        'list_view_even_row_color': '#FFFFFF',
        'list_view_odd_row_color': '#FFFFFF',

        'login_page_style': 'style_3',
        'loading_style':'style_9',
        'progress_style':'style_1',
        'progress_height':'4px',
        'progress_color': '#ED4762',
        'login_page_background_type': 'bg_img',
        # 'login_page_box_color':False,

        'modal_popup_style': 'style_1',
        'is_sticky_form': True,
        'is_sticky_chatter': True,
        'is_sticky_list': True,
        'is_sticky_list_inside_form': True,
        'horizontal_tab_style': 'style_7',
        'vertical_tab_style': 'style_7',
        'form_element_style': 'style_7',
        'breadcrumb_style': 'style_5',
        'search_style': 'expanded',
        'chatter_position':'normal'
    }

}

dict_theme_color_style = {

    'color_1_1': {

        'primary_color': '#2C3782',
        'primary_hover': '#141F76',
        'primary_active': '#141F76',
        'secondary_color': '#e2e4e6',
        'secondary_hover': '#e2e4e6',
        'secondary_active': '#e2e4e6',
        #        'header_background_color': '#ffffff',
        #        'body_background_color': '#ffffff',
        #        'header_font_color': '#a1a1a1',
        'header_hover_color': '#2C3782',
        'header_active_color': '#2C3782',
        #        'h1_color': '#4E4E4E',
        #        'h2_color': '#4E4E4E',
        #        'h3_color': '#4E4E4E',
        #        'h4_color': '#4E4E4E',
        #        'h5_color': '#4E4E4E',
        #        'h6_color': '#4E4E4E',
        #        'p_color': '#4E4E4E',
        'h1_size': 28,
        'h2_size': 17,
        'h3_size': 18,
        'h4_size': 13,
        'h5_size': 13,
        'h6_size': 12,
        'p_size': 13,

        'sidebar_is_show_nav_bar': True,
        'sidebar_collapse_style': 'collapsed',
        'sidebar_font_hover_background_color': '#2C3782',
        'sidebar_background_style': 'color',
        'sidebar_background_color': '#ffffff',
        'sidebar_font_color': '#181F4C',
        'sidebar_font_hover_color': '#ffffff',

        'separator_color': '#141F76',
        #        'separator_style': 'style_7',

        #        'button_style': 'style_1',
        #        'is_button_with_icon_text': True,

        #         'body_background_type':'bg_color',
        'body_font_color': '#787373',
        #         'body_font_family':'Roboto',
        #         'body_google_font_family':'Muli',
        #         'is_used_google_font':False,

        #         'list_view_border':'without_border',
        'list_view_is_hover_row': True,
        'list_view_hover_bg_color': '#f2f2f2',
        #         'list_view_even_row_color': '#FFFFFF',
        #         'list_view_odd_row_color': '#ffffff',

        #         'login_page_style': 'style_1',
        #         'login_page_background_type': 'bg_color',
        #         'login_page_box_color':False,

        #         'modal_popup_style':'style_1',
        'loading_style': 'style_1',
        'progress_style': 'style_1',
        'progress_height': '4px',
        'progress_color': '#2C3782',


    },
    'color_1_2': {

        'primary_color': '#2C3782',
        'primary_hover': '#141F76',
        'primary_active': '#141F76',
        'secondary_color': '#e2e4e6',
        'secondary_hover': '#e2e4e6',
        'secondary_active': '#e2e4e6',
        #        'header_background_color': '#ffffff',
        #        'body_background_color': '#ffffff',
        #        'header_font_color': '#a1a1a1',
        'header_hover_color': '#2C3782',
        'header_active_color': '#2C3782',
        #        'h1_color': '#262F5F',
        #        'h2_color': '#262F5F',
        #        'h3_color': '#262F5F',
        #        'h4_color': '#262F5F',
        #        'h5_color': '#262F5F',
        #        'h6_color': '#262F5F',
        #        'p_color': '#262F5F',
        'h1_size': 28,
        'h2_size': 17,
        'h3_size': 18,
        'h4_size': 13,
        'h5_size': 13,
        'h6_size': 12,
        'p_size': 13,

        'sidebar_is_show_nav_bar': True,
        'sidebar_collapse_style': 'expanded',
        'sidebar_background_color': '#FFFFFF',
        'sidebar_background_style': 'color',
        'sidebar_font_color': '#181F4C',
        'sidebar_font_hover_color': '#ffffff',
        'sidebar_font_hover_background_color': '#2C3782',

        #
        #         'button_style': 'style_2',
        #         'is_button_with_icon_text': True,
        #         'is_button_with_box_shadow': True,
        #
        #        'separator_style': 'style_7',
        'separator_color': '#141F76',
        #
        #        'body_background_type':'bg_color',
        'body_font_color': '#787373',
        #        'body_font_family':'Poppins',
        #        'body_google_font_family':'Muli',
        #        'is_used_google_font':False,
        #
        #        'list_view_border':'without_border',
        'list_view_is_hover_row': True,
        'list_view_hover_bg_color': '#f2f2f2',
        #        'list_view_even_row_color': '#FFFFFF',
        #        'list_view_odd_row_color': '#ffffff',
        #
        #        'login_page_style': 'style_1',
        #        'login_page_background_type': 'bg_color',
        #        'login_page_box_color':False,
        #
        #
        #        'modal_popup_style':'style_2'
        'loading_style': 'style_4',
        'progress_style': 'style_1',
        'progress_height': '4px',
        'progress_color': '#2C3782',
    },
    'color_1_3': {
        'primary_color': '#2C3782',
        'primary_hover': '#141F76',
        'primary_active': '#141F76',
        'secondary_color': '#e2e4e6',
        'secondary_hover': '#e2e4e6',
        'secondary_active': '#e2e4e6',
        #        'header_background_color': '#ffffff',
        #        'body_background_color': '#ffffff',
        #        'header_font_color': '#a1a1a1',
        'header_hover_color': '#2C3782',
        'header_active_color': '#2C3782',
        #        'h1_color': '#4E4E4E',
        #        'h2_color': '#4E4E4E',
        #        'h3_color': '#4E4E4E',
        #        'h4_color': '#4E4E4E',
        #        'h5_color': '#4E4E4E',
        #        'h6_color': '#4E4E4E',
        #        'p_color': '#4E4E4E',
        'h1_size': 28,
        'h2_size': 17,
        'h3_size': 18,
        'h4_size': 13,
        'h5_size': 13,
        'h6_size': 12,
        'p_size': 13,
        #
        'sidebar_is_show_nav_bar': True,
        'sidebar_collapse_style': 'collapsed',
        #        'sidebar_background_color': '#ffffff',
        'sidebar_background_style': 'image',
        'sidebar_font_color': '#181F4C',
        'sidebar_font_hover_color': '#2C3782',
        'sidebar_font_hover_background_color': '#fafafa',

        #
        #         'button_style': 'style_1',
        #         'is_button_with_icon_text': True,
        #
        #        'separator_style': 'style_7',
        'separator_color': '#141F76',
        #
        #        'body_background_type':'bg_color',
        #        'body_font_family':'Roboto',
        'body_font_color': '#787373',
        #        'body_google_font_family':'Muli',
        #        'is_used_google_font':False,
        #
        #        'list_view_border':'without_border',
        'list_view_is_hover_row': True,
        'list_view_hover_bg_color': '#f2f2f2',
        #        'list_view_even_row_color': '#FFFFFF',
        #        'list_view_odd_row_color': '#ffffff',
        #
        #        'login_page_style': 'style_1',
        #        'login_page_background_type': 'bg_color',
        #        'login_page_box_color':False,
        #
        #
        #        'modal_popup_style':'style_1'
        'loading_style': 'style_9',
        'progress_style': 'style_1',
        'progress_height': '4px',
        'progress_color': '#2C3782',
    },
    'color_2_1': {
        'primary_color': '#ff9800',
        'primary_hover': '#F29107',
        'primary_active': '#F29107',
        'secondary_color': '#e2e4e6',
        'secondary_hover': '#e2e4e6',
        'secondary_active': '#e2e4e6',
        #        'header_background_color': '#ffffff',
        #        'body_background_color': '#ffffff',
        #        'header_font_color': '#a1a1a1',
        'header_hover_color': '#ff9800',
        'header_active_color': '#ff9800',
        #        'h1_color': '#4E4E4E',
        #        'h2_color': '#4E4E4E',
        #        'h3_color': '#4E4E4E',
        #        'h4_color': '#4E4E4E',
        #        'h5_color': '#4E4E4E',
        #        'h6_color': '#4E4E4E',
        #        'p_color': '#4E4E4E',
        'h1_size': 28,
        'h2_size': 17,
        'h3_size': 18,
        'h4_size': 13,
        'h5_size': 13,
        'h6_size': 12,
        'p_size': 13,

        'sidebar_is_show_nav_bar': True,
        'sidebar_collapse_style': 'collapsed',
        'sidebar_font_hover_background_color': '#ff9800',
        'sidebar_background_style': 'color',
        'sidebar_background_color': '#ffffff',
        'sidebar_font_color': '#181F4C',
        'sidebar_font_hover_color': '#ffffff',
        #
        #        'separator_color': '#F29107',
        'separator_style': 'style_7',
        #
        #        'button_style': 'style_1',
        #        'is_button_with_icon_text': True,
        #
        #         'body_background_type':'bg_color',
        #         'body_font_family':'Roboto',
        'body_font_color': '#787373',
        #         'body_google_font_family':'Muli',
        #         'is_used_google_font':False,
        #
        #         'list_view_border':'without_border',
        'list_view_is_hover_row': True,
        'list_view_hover_bg_color': '#f2f2f2',
        #         'list_view_even_row_color': '#FFFFFF',
        #         'list_view_odd_row_color': '#ffffff',
        #
        #         'login_page_style': 'style_1',
        #         'login_page_background_type': 'bg_color',
        #         'login_page_box_color':False,
        #
        #         'modal_popup_style':'style_1',
        'loading_style': 'style_1',
        'progress_style': 'style_1',
        'progress_height': '4px',
        'progress_color': '#ff9800',
    },
    'color_2_2': {
        'primary_color': '#ff9800',
        'primary_hover': '#F29107',
        'primary_active': '#F29107',
        'secondary_color': '#e2e4e6',
        'secondary_hover': '#e2e4e6',
        'secondary_active': '#e2e4e6',
        #        'header_background_color': '#ffffff',
        #        'body_background_color': '#ffffff',
        #        'header_font_color': '#a1a1a1',
        'header_hover_color': '#ff9800',
        'header_active_color': '#ff9800',
        #        'h1_color': '#4E4E4E',
        #        'h2_color': '#4E4E4E',
        #        'h3_color': '#4E4E4E',
        #        'h4_color': '#4E4E4E',
        #        'h5_color': '#4E4E4E',
        #        'h6_color': '#4E4E4E',
        #        'p_color': '#4E4E4E',
        'h1_size': 28,
        'h2_size': 17,
        'h3_size': 18,
        'h4_size': 13,
        'h5_size': 13,
        'h6_size': 12,
        'p_size': 13,

        'sidebar_is_show_nav_bar': True,
        'sidebar_collapse_style': 'expanded',
        'sidebar_background_color': '#FFFFFF',
        'sidebar_background_style': 'color',
        'sidebar_font_color': '#181F4C',
        'sidebar_font_hover_color': '#ffffff',
        'sidebar_font_hover_background_color': '#F29107',


        #
        #          'button_style': 'style_2',
        #         'is_button_with_icon_text': True,
        #         'is_button_with_box_shadow': True,
        #
        #        'separator_style': 'style_7',
        'separator_color': '#F29107',
        #
        #        'body_background_type':'bg_color',
        #        'body_font_family':'Roboto',
        'body_font_color': '#787373',
        #        'body_google_font_family':'Muli',
        #        'is_used_google_font':False,
        #
        #        'list_view_border':'without_border',
        'list_view_is_hover_row': True,
        'list_view_hover_bg_color': '#f2f2f2',
        #        'list_view_even_row_color': '#FFFFFF',
        #        'list_view_odd_row_color': '#ffffff',
        #
        #        'login_page_style': 'style_1',
        #        'login_page_background_type': 'bg_color',
        #        'login_page_box_color':False,
        #

        #        'modal_popup_style':'style_1'
        'loading_style': 'style_4',
        'progress_style': 'style_1',
        'progress_height': '4px',
        'progress_color': '#ff9800',
    },
    'color_2_3': {
        'primary_color': '#ff9800',
        'primary_hover': '#F29107',
        'primary_active': '#F29107',
        'secondary_color': '#e2e4e6',
        'secondary_hover': '#e2e4e6',
        'secondary_active': '#e2e4e6',
        #        'header_background_color': '#ffffff',
        #        'body_background_color': '#ffffff',
        #        'header_font_color': '#a1a1a1',
        'header_hover_color': '#ff9800',
        'header_active_color': '#ff9800',
        #        'h1_color': '#4E4E4E',
        #        'h2_color': '#4E4E4E',
        #        'h3_color': '#4E4E4E',
        #        'h4_color': '#4E4E4E',
        #        'h5_color': '#4E4E4E',
        #        'h6_color': '#4E4E4E',
        #        'p_color': '#4E4E4E',
        'h1_size': 28,
        'h2_size': 17,
        'h3_size': 18,
        'h4_size': 13,
        'h5_size': 13,
        'h6_size': 12,
        'p_size': 13,

        'sidebar_is_show_nav_bar': True,
        'sidebar_collapse_style': 'collapsed',
        #        'sidebar_background_color': '#ffffff',
        'sidebar_background_style': 'image',
        'sidebar_font_color': '#181F4C',
        'sidebar_font_hover_color': '#ff9800',
        'sidebar_font_hover_background_color': '#fafafa',

        #
        #         'button_style': 'style_1',
        #         'is_button_with_icon_text': True,
        #
        #        'separator_style': 'style_7',
        'separator_color': '#F29107',
        #
        #        'body_background_type':'bg_color',
        #        'body_font_family':'Roboto',
        'body_font_color': '#787373',
        #        'body_google_font_family':'Muli',
        #        'is_used_google_font':False,
        #
        #        'list_view_border':'without_border',
        'list_view_is_hover_row': True,
        'list_view_hover_bg_color': '#f2f2f2',
        #        'list_view_even_row_color': '#FFFFFF',
        #        'list_view_odd_row_color': '#ffffff',
        #
        #        'login_page_style': 'style_1',
        #        'login_page_background_type': 'bg_color',
        #        'login_page_box_color':False,
        #
        #
        #        'modal_popup_style':'style_1'
        'loading_style': 'style_9',
        'progress_style': 'style_1',
        'progress_height': '4px',
        'progress_color': '#ff9800',
    },
    'color_3_1': {
        'primary_color': '#ED4762',
        'primary_hover': '#DD3C54',
        'primary_active': '#DD3C54',
        'gradient_color': '#4F2499',
        'secondary_color': '#e2e4e6',
        'secondary_hover': '#e2e4e6',
        'secondary_active': '#e2e4e6',
        #        'header_background_color': '#ffffff',
        #        'body_background_color': '#ffffff',
        #        'header_font_color': '#a1a1a1',
        'header_hover_color': '#ED4762',
        'header_active_color': '#ED4762',
        #        'h1_color': '#4E4E4E',
        #        'h2_color': '#4E4E4E',
        #        'h3_color': '#4E4E4E',
        #        'h4_color': '#4E4E4E',
        #        'h5_color': '#4E4E4E',
        #        'h6_color': '#4E4E4E',
        #        'p_color': '#4E4E4E',
        'h1_size': 28,
        'h2_size': 17,
        'h3_size': 18,
        'h4_size': 13,
        'h5_size': 13,
        'h6_size': 12,
        'p_size': 13,

        'sidebar_is_show_nav_bar': True,
        'sidebar_collapse_style': 'collapsed',
        'sidebar_font_hover_background_color': '#ED4762',
        'sidebar_background_style': 'color',
        'sidebar_background_color': '#ffffff',
        'sidebar_font_color': '#181F4C',
        'sidebar_font_hover_color': '#ffffff',
        #
        #        'separator_color': '#DD3C54',
        'separator_style': 'style_7',
        #
        #        'button_style': 'style_1',
        #        'is_button_with_icon_text': True,
        #
        #         'body_background_type':'bg_color',
        #         'body_font_family':'Roboto',
        'body_font_color': '#787373',
        #         'body_google_font_family':'Muli',
        #         'is_used_google_font':False,
        #
        #         'list_view_border':'without_border',
        'list_view_is_hover_row': True,
        'list_view_hover_bg_color': '#f2f2f2',
        #         'list_view_even_row_color': '#FFFFFF',
        #         'list_view_odd_row_color': '#ffffff',
        #
        #         'login_page_style': 'style_1',
        #         'login_page_background_type': 'bg_color',
        #         'login_page_box_color':False,
        #
        #         'modal_popup_style':'style_1',
        'loading_style': 'style_1',
        'progress_style': 'style_1',
        'progress_height': '4px',
        'progress_color': '#ED4762',
    },
    'color_3_2': {
        'primary_color': '#ED4762',
        'primary_hover': '#DD3C54',
        'primary_active': '#DD3C54',
        'gradient_color': '#4F2499',
        'secondary_color': '#e2e4e6',
        'secondary_hover': '#e2e4e6',
        'secondary_active': '#e2e4e6',
        #        'header_background_color': '#ffffff',
        #        'body_background_color': '#ffffff',
        #        'header_font_color': '#a1a1a1',
        'header_hover_color': '#ED4762',
        'header_active_color': '#ED4762',
        #        'h1_color': '#4E4E4E',
        #        'h2_color': '#4E4E4E',
        #        'h3_color': '#4E4E4E',
        #        'h4_color': '#4E4E4E',
        #        'h5_color': '#4E4E4E',
        #        'h6_color': '#4E4E4E',
        #        'p_color': '#4E4E4E',
        'h1_size': 28,
        'h2_size': 17,
        'h3_size': 18,
        'h4_size': 13,
        'h5_size': 13,
        'h6_size': 12,
        'p_size': 13,
        #
        'sidebar_is_show_nav_bar': True,
        'sidebar_collapse_style': 'expanded',
        'sidebar_background_color': '#ffffff',
        'sidebar_background_style': 'color',
        'sidebar_font_color': '#181F4C',
        'sidebar_font_hover_color': '#ffffff',
        'sidebar_font_hover_background_color': '#DD3C54',

        #
        #          'button_style': 'style_2',
        #         'is_button_with_icon_text': True,
        #         'is_button_with_box_shadow': True,
        #
        #        'separator_style': 'style_7',
        'separator_color': '#DD3C54',
        #
        #        'body_background_type':'bg_color',
        #        'body_font_family':'Roboto',
        'body_font_color': '#787373',
        #        'body_google_font_family':'Muli',
        #        'is_used_google_font':False,
        #
        #        'list_view_border':'without_border',
        'list_view_is_hover_row': True,
        'list_view_hover_bg_color': '#f2f2f2',
        #        'list_view_even_row_color': '#FFFFFF',
        #        'list_view_odd_row_color': '#ffffff',
        #
        #        'login_page_style': 'style_1',
        #        'login_page_background_type': 'bg_color',
        #        'login_page_box_color':False,
        #
        #
        #        'modal_popup_style':'style_1'
        'loading_style': 'style_4',
        'progress_style': 'style_1',
        'progress_height': '4px',
        'progress_color': '#ED4762',
    },
    'color_3_3': {
        'primary_color': '#ED4762',
        'primary_hover': '#DD3C54',
        'primary_active': '#DD3C54',
        'gradient_color': '#4F2499',
        'secondary_color': '#e2e4e6',
        'secondary_hover': '#e2e4e6',
        'secondary_active': '#e2e4e6',
        #        'header_background_color': '#ffffff',
        #        'body_background_color': '#ffffff',
        #        'header_font_color': '#a1a1a1',
        'header_hover_color': '#ED4762',
        'header_active_color': '#ED4762',
        #        'h1_color': '#4E4E4E',
        #        'h2_color': '#4E4E4E',
        #        'h3_color': '#4E4E4E',
        #        'h4_color': '#4E4E4E',
        #        'h5_color': '#4E4E4E',
        #        'h6_color': '#4E4E4E',
        #        'p_color': '#4E4E4E',
        'h1_size': 28,
        'h2_size': 17,
        'h3_size': 18,
        'h4_size': 13,
        'h5_size': 13,
        'h6_size': 12,
        'p_size': 13,

        'sidebar_is_show_nav_bar': False,
        'sidebar_collapse_style': 'collapsed',
        #        'sidebar_background_color': '#ffffff',
        'sidebar_background_style': 'image',
        'sidebar_font_color': '#181F4C',
        'sidebar_font_hover_color': '#ED4762',
        'sidebar_font_hover_background_color': '#fafafa',
        #
        #
        #         'button_style': 'style_1',
        #         'is_button_with_icon_text': True,
        #
        #        'separator_style': 'style_7',
        'separator_color': '#DD3C54',
        #
        #        'body_background_type':'bg_color',
        #        'body_font_family':'Roboto',
        'body_font_color': '#787373',
        #        'body_google_font_family':'Muli',
        #        'is_used_google_font':False,
        #
        #        'list_view_border':'without_border',
        'list_view_is_hover_row': True,
        'list_view_hover_bg_color': '#f2f2f2',
        #        'list_view_even_row_color': '#FFFFFF',
        #        'list_view_odd_row_color': '#ffffff',
        #
        #        'login_page_style': 'style_1',
        #        'login_page_background_type': 'bg_color',
        #        'login_page_box_color':False,
        #
        #
        #        'modal_popup_style':'style_1'
        'loading_style': 'style_9',
        'progress_style': 'style_1',
        'progress_height': '4px',
        'progress_color': '#ED4762',
    },
    'color_4_1': {
        'primary_color': '#673AB7',
        'primary_hover': '#5C32A9',
        'primary_active': '#5C32A9',
        'secondary_color': '#e2e4e6',
        'secondary_hover': '#e2e4e6',
        'secondary_active': '#e2e4e6',
        #        'header_background_color': '#ffffff',
        #        'body_background_color': '#ffffff',
        #        'header_font_color': '#a1a1a1',
        'header_hover_color': '#673AB7',
        'header_active_color': '#673AB7',
        #        'h1_color': '#4E4E4E',
        #        'h2_color': '#4E4E4E',
        #        'h3_color': '#4E4E4E',
        #        'h4_color': '#4E4E4E',
        #        'h5_color': '#4E4E4E',
        #        'h6_color': '#4E4E4E',
        #        'p_color': '#4E4E4E',
        'h1_size': 28,
        'h2_size': 17,
        'h3_size': 18,
        'h4_size': 13,
        'h5_size': 13,
        'h6_size': 12,
        'p_size': 13,

        'sidebar_is_show_nav_bar': True,
        'sidebar_collapse_style': 'collapsed',
        'sidebar_font_hover_background_color': '#673AB7',
        'sidebar_background_style': 'color',
        'sidebar_background_color': '#ffffff',
        'sidebar_font_color': '#181F4C',
        'sidebar_font_hover_color': '#ffffff',
        #
        'separator_color': '#5C32A9',
        #        'separator_style': 'style_7',
        #
        #        'button_style': 'style_1',
        #        'is_button_with_icon_text': True,
        #
        #         'body_background_type':'bg_color',
        #         'body_font_family':'Roboto',
        'body_font_color': '#787373',
        #         'body_google_font_family':'Muli',
        #         'is_used_google_font':False,
        #
        #         'list_view_border':'without_border',
        'list_view_is_hover_row': True,
        'list_view_hover_bg_color': '#f2f2f2',
        #         'list_view_even_row_color': '#FFFFFF',
        #         'list_view_odd_row_color': '#ffffff',
        #
        #         'login_page_style': 'style_1',
        #         'login_page_background_type': 'bg_color',
        #         'login_page_box_color':False,
        #
        #         'modal_popup_style':'style_1',
        'loading_style': 'style_1',
        'progress_style': 'style_1',
        'progress_height': '4px',
        'progress_color': '#673AB7',
    },
    'color_4_2': {
        'primary_color': '#673AB7',
        'primary_hover': '#5C32A9',
        'primary_active': '#5C32A9',
        'secondary_color': '#e2e4e6',
        'secondary_hover': '#e2e4e6',
        'secondary_active': '#e2e4e6',
        #        'header_background_color': '#ffffff',
        #        'body_background_color': '#ffffff',
        #        'header_font_color': '#a1a1a1',
        'header_hover_color': '#673AB7',
        'header_active_color': '#673AB7',
        #        'h1_color': '#4E4E4E',
        #        'h2_color': '#4E4E4E',
        #        'h3_color': '#4E4E4E',
        #        'h4_color': '#4E4E4E',
        #        'h5_color': '#4E4E4E',
        #        'h6_color': '#4E4E4E',
        #        'p_color': '#4E4E4E',
        'h1_size': 28,
        'h2_size': 17,
        'h3_size': 18,
        'h4_size': 13,
        'h5_size': 13,
        'h6_size': 12,
        'p_size': 13,

        'sidebar_is_show_nav_bar': True,
        'sidebar_collapse_style': 'expanded',
        'sidebar_background_color': '#ffffff',
        'sidebar_background_style': 'color',
        'sidebar_font_color': '#181F4C',
        'sidebar_font_hover_color': '#ffffff',
        'sidebar_font_hover_background_color': '#5C32A9',
        #
        #
        #          'button_style': 'style_2',
        #         'is_button_with_icon_text': True,
        #         'is_button_with_box_shadow': True,
        #
        #        'separator_style': 'style_7',
        'separator_color': '#5C32A9',
        #
        #        'body_background_type':'bg_color',
        #        'body_font_family':'Roboto',
        'body_font_color': '#787373',
        #        'body_google_font_family':'Muli',
        #        'is_used_google_font':False,
        #
        #        'list_view_border':'without_border',
        'list_view_is_hover_row': True,
        'list_view_hover_bg_color': '#f2f2f2',
        #        'list_view_even_row_color': '#FFFFFF',
        #        'list_view_odd_row_color': '#ffffff',
        #
        #        'login_page_style': 'style_1',
        #        'login_page_background_type': 'bg_color',
        #        'login_page_box_color':False,
        #
        #
        #        'modal_popup_style':'style_1'
        'loading_style': 'style_4',
        'progress_style': 'style_1',
        'progress_height': '4px',
        'progress_color': '#673AB7',
    },
    'color_4_3': {
        'primary_color': '#673AB7',
        'primary_hover': '#5C32A9',
        'primary_active': '#5C32A9',
        'secondary_color': '#e2e4e6',
        'secondary_hover': '#e2e4e6',
        'secondary_active': '#e2e4e6',
        #        'header_background_color': '#ffffff',
        #        'body_background_color': '#ffffff',
        #        'header_font_color': '#a1a1a1',
        'header_hover_color': '#673AB7',
        'header_active_color': '#673AB7',
        #        'h1_color': '#4E4E4E',
        #        'h2_color': '#4E4E4E',
        #        'h3_color': '#4E4E4E',
        #        'h4_color': '#4E4E4E',
        #        'h5_color': '#4E4E4E',
        #        'h6_color': '#4E4E4E',
        #        'p_color': '#4E4E4E',
        'h1_size': 28,
        'h2_size': 17,
        'h3_size': 18,
        'h4_size': 13,
        'h5_size': 13,
        'h6_size': 12,
        'p_size': 13,

        'sidebar_is_show_nav_bar': True,
        'sidebar_collapse_style': 'collapsed',
        #        'sidebar_background_color': '#ffffff',
        'sidebar_background_style': 'image',
        'sidebar_font_color': '#181F4C',
        'sidebar_font_hover_color': '#673AB7',
        'sidebar_font_hover_background_color': '#fafafa',
        #
        #
        #         'button_style': 'style_1',
        #         'is_button_with_icon_text': True,
        #
        #        'separator_style': 'style_7',
        'separator_color': '#5C32A9',
        #
        #        'body_background_type':'bg_color',
        #        'body_font_family':'Roboto',
        'body_font_color': '#787373',
        #        'body_google_font_family':'Muli',
        #        'is_used_google_font':False,
        #
        #        'list_view_border':'without_border',
        'list_view_is_hover_row': True,
        'list_view_hover_bg_color': '#f2f2f2',
        #        'list_view_even_row_color': '#FFFFFF',
        #        'list_view_odd_row_color': '#ffffff',
        #
        #        'login_page_style': 'style_1',
        #        'login_page_background_type': 'bg_color',
        #        'login_page_box_color':False,
        #
        #
        #        'modal_popup_style':'style_1'
        'loading_style': 'style_9',
        'progress_style': 'style_1',
        'progress_height': '4px',
        'progress_color': '#673AB7',
    },
    'color_5_1': {
        'primary_color': '#5d4037',
        'primary_hover': '#56343C',
        'primary_active': '#56343C',
        'secondary_color': '#e2e4e6',
        'secondary_hover': '#e2e4e6',
        'secondary_active': '#e2e4e6',
        #        'header_background_color': '#ffffff',
        #        'body_background_color': '#ffffff',
        #        'header_font_color': '#a1a1a1',
        'header_hover_color': '#5d4037',
        'header_active_color': '#5d4037',
        #        'h1_color': '#4E4E4E',
        #        'h2_color': '#4E4E4E',
        #        'h3_color': '#4E4E4E',
        #        'h4_color': '#4E4E4E',
        #        'h5_color': '#4E4E4E',
        #        'h6_color': '#4E4E4E',
        #        'p_color': '#4E4E4E',
        'h1_size': 28,
        'h2_size': 17,
        'h3_size': 18,
        'h4_size': 13,
        'h5_size': 13,
        'h6_size': 12,
        'p_size': 13,

        'sidebar_is_show_nav_bar': True,
        'sidebar_collapse_style': 'collapsed',
        'sidebar_font_hover_background_color': '#5d4037',
        'sidebar_background_style': 'color',
        'sidebar_background_color': '#ffffff',
        'sidebar_font_color': '#181F4C',
        'sidebar_font_hover_color': '#ffffff',
        #
        'separator_color': '#56343C',
        #        'separator_style': 'style_7',
        #
        #        'button_style': 'style_1',
        #        'is_button_with_icon_text': True,
        #
        #         'body_background_type':'bg_color',
        #         'body_font_family':'Roboto',
        'body_font_color': '#787373',
        #         'body_google_font_family':'Muli',
        #         'is_used_google_font':False,
        #
        #         'list_view_border':'without_border',
        'list_view_is_hover_row': True,
        'list_view_hover_bg_color': '#f2f2f2',
        #         'list_view_even_row_color': '#FFFFFF',
        #         'list_view_odd_row_color': '#ffffff',
        #
        #         'login_page_style': 'style_1',
        #         'login_page_background_type': 'bg_color',
        #         'login_page_box_color':False,
        #
        #         'modal_popup_style':'style_1',
        'loading_style': 'style_1',
        'progress_style': 'style_1',
        'progress_height': '4px',
        'progress_color': '#5d4037',
    },
    'color_5_2': {
        'primary_color': '#5d4037',
        'primary_hover': '#56343C',
        'primary_active': '#56343C',
        'secondary_color': '#e2e4e6',
        'secondary_hover': '#e2e4e6',
        'secondary_active': '#e2e4e6',
        #        'header_background_color': '#ffffff',
        #        'body_background_color': '#ffffff',
        #        'header_font_color': '#a1a1a1',
        'header_hover_color': '#5d4037',
        'header_active_color': '#5d4037',
        #        'h1_color': '#4E4E4E',
        #        'h2_color': '#4E4E4E',
        #        'h3_color': '#4E4E4E',
        #        'h4_color': '#4E4E4E',
        #        'h5_color': '#4E4E4E',
        #        'h6_color': '#4E4E4E',
        #        'p_color': '#4E4E4E',
        'h1_size': 28,
        'h2_size': 17,
        'h3_size': 18,
        'h4_size': 13,
        'h5_size': 13,
        'h6_size': 12,
        'p_size': 13,
        #
        'sidebar_is_show_nav_bar': True,
        'sidebar_collapse_style': 'expanded',
        'sidebar_background_style': 'color',
        'sidebar_background_color': '#ffffff',
        'sidebar_font_color': '#181F4C',
        'sidebar_font_hover_color': '#ffffff',
        'sidebar_font_hover_background_color': '#56343C',

        #
        #         'button_style': 'style_2',
        #         'is_button_with_icon_text': True,
        #         'is_button_with_box_shadow': True,
        #
        #        'separator_style': 'style_7',
        'separator_color': '#56343C',
        #
        #        'body_background_type':'bg_color',
        #        'body_font_family':'Roboto',
        'body_font_color': '#787373',
        #        'body_google_font_family':'Muli',
        #        'is_used_google_font':False,
        #
        #        'list_view_border':'without_border',
        'list_view_is_hover_row': True,
        'list_view_hover_bg_color': '#f2f2f2',
        #        'list_view_even_row_color': '#FFFFFF',
        #        'list_view_odd_row_color': '#ffffff',
        #
        #        'login_page_style': 'style_1',
        #        'login_page_background_type': 'bg_color',
        #        'login_page_box_color':False,
        #
        #
        #        'modal_popup_style':'style_1'
        'loading_style': 'style_4',
        'progress_style': 'style_1',
        'progress_height': '4px',
        'progress_color': '#5d4037',
    },
    'color_5_3': {
        'primary_color': '#5d4037',
        'primary_hover': '#56343C',
        'primary_active': '#56343C',
        'secondary_color': '#e2e4e6',
        'secondary_hover': '#e2e4e6',
        'secondary_active': '#e2e4e6',
        #        'header_background_color': '#ffffff',
        #        'body_background_color': '#ffffff',
        #        'header_font_color': '#a1a1a1',
        'header_hover_color': '#5d4037',
        'header_active_color': '#5d4037',
        #        'h1_color': '#4E4E4E',
        #        'h2_color': '#4E4E4E',
        #        'h3_color': '#4E4E4E',
        #        'h4_color': '#4E4E4E',
        #        'h5_color': '#4E4E4E',
        #        'h6_color': '#4E4E4E',
        #        'p_color': '#4E4E4E',
        'h1_size': 28,
        'h2_size': 17,
        'h3_size': 18,
        'h4_size': 13,
        'h5_size': 13,
        'h6_size': 12,
        'p_size': 13,

        'sidebar_is_show_nav_bar': True,
        'sidebar_collapse_style': 'collapsed',
        #        'sidebar_background_color': '#ffffff',
        'sidebar_background_style': 'image',
        'sidebar_font_color': '#181F4C',
        'sidebar_font_hover_color': '47336B',
        'sidebar_font_hover_background_color': '#fafafa',

        #
        #         'button_style': 'style_1',
        #         'is_button_with_icon_text': True,
        #
        #        'separator_style': 'style_7',
        'separator_color': '#56343C',
        #
        #        'body_background_type':'bg_color',
        #        'body_font_family':'Roboto',
        'body_font_color': '#787373',
        #        'body_google_font_family':'Muli',
        #        'is_used_google_font':False,
        #
        #        'list_view_border':'without_border',
        'list_view_is_hover_row': True,
        'list_view_hover_bg_color': '#f2f2f2',
        #        'list_view_even_row_color': '#FFFFFF',
        #        'list_view_odd_row_color': '#ffffff',
        #
        #        'login_page_style': 'style_1',
        #        'login_page_background_type': 'bg_color',
        #        'login_page_box_color':False,
        #
        #
        #        'modal_popup_style':'style_1'
        'loading_style': 'style_9',
        'progress_style': 'style_1',
        'progress_height': '4px',
        'progress_color': '#5d4037',
    },
    'color_6_1': {
        'primary_color': '#5B6DDB',
        'primary_hover': '#505DBE',
        'primary_active': '#505DBE',
        'secondary_color': '#e2e4e6',
        'secondary_hover': '#e2e4e6',
        'secondary_active': '#e2e4e6',
        #        'header_background_color': '#ffffff',
        #        'body_background_color': '#ffffff',
        #        'header_font_color': '#a1a1a1',
        'header_hover_color': '#5B6DDB',
        'header_active_color': '#5B6DDB',
        #        'h1_color': '#4E4E4E',
        #        'h2_color': '#4E4E4E',
        #        'h3_color': '#4E4E4E',
        #        'h4_color': '#4E4E4E',
        #        'h5_color': '#4E4E4E',
        #        'h6_color': '#4E4E4E',
        #        'p_color': '#4E4E4E',
        'h1_size': 28,
        'h2_size': 17,
        'h3_size': 18,
        'h4_size': 13,
        'h5_size': 13,
        'h6_size': 12,
        'p_size': 13,

        'sidebar_is_show_nav_bar': True,
        'sidebar_collapse_style': 'collapsed',
        'sidebar_font_hover_background_color': '#5B6DDB',
        'sidebar_background_style': 'color',
        'sidebar_background_color': '#ffffff',
        'sidebar_font_color': '#181F4C',
        'sidebar_font_hover_color': '#ffffff',

        'separator_color': '#505DBE',
        #        'separator_style': 'style_7',
        #
        #        'button_style': 'style_1',
        #        'is_button_with_icon_text': True,
        #
        #         'body_background_type':'bg_color',
        #         'body_font_family':'Roboto',
        'body_font_color': '#787373',
        #         'body_google_font_family':'Muli',
        #         'is_used_google_font':False,
        #
        #         'list_view_border':'without_border',
        'list_view_is_hover_row': True,
        'list_view_hover_bg_color': '#f2f2f2',
        #         'list_view_even_row_color': '#FFFFFF',
        #         'list_view_odd_row_color': '#ffffff',
        #
        #         'login_page_style': 'style_1',
        #         'login_page_background_type': 'bg_color',
        #         'login_page_box_color':False,
        #
        #         'modal_popup_style':'style_1',
        'loading_style': 'style_1',
        'progress_style': 'style_1',
        'progress_height': '4px',
        'progress_color': '#5B6DDB',
    },
    'color_6_2': {
        'primary_color': '#5B6DDB',
        'primary_hover': '#505DBE',
        'primary_active': '#505DBE',
        'secondary_color': '#e2e4e6',
        'secondary_hover': '#e2e4e6',
        'secondary_active': '#e2e4e6',
        #        'header_background_color': '#ffffff',
        #        'body_background_color': '#ffffff',
        #        'header_font_color': '#a1a1a1',
        'header_hover_color': '#5B6DDB',
        'header_active_color': '#5B6DDB',
        #        'h1_color': '#4E4E4E',
        #        'h2_color': '#4E4E4E',
        #        'h3_color': '#4E4E4E',
        #        'h4_color': '#4E4E4E',
        #        'h5_color': '#4E4E4E',
        #        'h6_color': '#4E4E4E',
        #        'p_color': '#4E4E4E',
        'h1_size': 28,
        'h2_size': 17,
        'h3_size': 18,
        'h4_size': 13,
        'h5_size': 13,
        'h6_size': 12,
        'p_size': 13,

        'sidebar_is_show_nav_bar': True,
        'sidebar_collapse_style': 'expanded',
        'sidebar_background_color': '#ffffff',
        'sidebar_background_style': 'color',
        'sidebar_font_color': '#181F4C',
        'sidebar_font_hover_color': '#ffffff',
        'sidebar_font_hover_background_color': '#505DBE',

        #
        #         'button_style': 'style_2',
        #         'is_button_with_icon_text': True,
        #         'is_button_with_box_shadow': True,
        #        'separator_style': 'style_7',
        'separator_color': '#505DBE',
        #
        #        'body_background_type':'bg_color',
        #        'body_font_family':'Roboto',
        'body_font_color': '#787373',
        #        'body_google_font_family':'Muli',
        #        'is_used_google_font':False,
        #
        #        'list_view_border':'without_border',
        'list_view_is_hover_row': True,
        'list_view_hover_bg_color': '#f2f2f2',
        #        'list_view_even_row_color': '#FFFFFF',
        #        'list_view_odd_row_color': '#ffffff',
        #
        #        'login_page_style': 'style_1',
        #        'login_page_background_type': 'bg_color',
        #        'login_page_box_color':False,
        #
        #
        #        'modal_popup_style':'style_1'
        'loading_style': 'style_4',
        'progress_style': 'style_1',
        'progress_height': '4px',
        'progress_color': '#5B6DDB',
    },
    'color_6_3': {
        'primary_color': '#5B6DDB',
        'primary_hover': '#505DBE',
        'primary_active': '#505DBE',
        'secondary_color': '#e2e4e6',
        'secondary_hover': '#e2e4e6',
        'secondary_active': '#e2e4e6',
        #        'header_background_color': '#ffffff',
        #        'body_background_color': '#ffffff',
        #        'header_font_color': '#a1a1a1',
        'header_hover_color': '#5B6DDB',
        'header_active_color': '#5B6DDB',
        #        'h1_color': '#4E4E4E',
        #        'h2_color': '#4E4E4E',
        #        'h3_color': '#4E4E4E',
        #        'h4_color': '#4E4E4E',
        #        'h5_color': '#4E4E4E',
        #        'h6_color': '#4E4E4E',
        #        'p_color': '#4E4E4E',
        'h1_size': 28,
        'h2_size': 17,
        'h3_size': 18,
        'h4_size': 13,
        'h5_size': 13,
        'h6_size': 12,
        'p_size': 13,
        #
        'sidebar_is_show_nav_bar': True,
        'sidebar_collapse_style': 'collapsed',
        #        'sidebar_background_color': '#ffffff',
        'sidebar_background_style': 'image',
        'sidebar_font_color': '#181F4C',
        'sidebar_font_hover_color': '#5B6DDB',
        'sidebar_font_hover_background_color': '#fafafa',

        #
        #         'button_style': 'style_1',
        #         'is_button_with_icon_text': True,
        #
        #        'separator_style': 'style_7',
        'separator_color': '#505DBE',
        #
        #        'body_background_type':'bg_color',
        #        'body_font_family':'Roboto',
        'body_font_color': '#787373',
        #        'body_google_font_family':'Muli',
        #        'is_used_google_font':False,
        #
        #        'list_view_border':'without_border',
        'list_view_is_hover_row': True,
        'list_view_hover_bg_color': '#f2f2f2',
        #        'list_view_even_row_color': '#FFFFFF',
        #        'list_view_odd_row_color': '#ffffff',
        #
        #        'login_page_style': 'style_1',
        #        'login_page_background_type': 'bg_color',
        #        'login_page_box_color':False,
        #
        #
        #        'modal_popup_style':'style_1'
        'loading_style': 'style_9',
        'progress_style': 'style_1',
        'progress_height': '4px',
        'progress_color': '#5B6DDB',
    },

    'color_7_1': {
        'primary_color': '#43A047',
        'primary_hover': '#3B9141',
        'primary_active': '#3B9141',
        'secondary_color': '#e2e4e6',
        'secondary_hover': '#e2e4e6',
        'secondary_active': '#e2e4e6',
        #        'header_background_color': '#ffffff',
        #        'body_background_color': '#ffffff',
        #        'header_font_color': '#a1a1a1',
        'header_hover_color': '#43A047',
        'header_active_color': '#43A047',
        #        'h1_color': '#4E4E4E',
        #        'h2_color': '#4E4E4E',
        #        'h3_color': '#4E4E4E',
        #        'h4_color': '#4E4E4E',
        #        'h5_color': '#4E4E4E',
        #        'h6_color': '#4E4E4E',
        #        'p_color': '#4E4E4E',
        'h1_size': 28,
        'h2_size': 17,
        'h3_size': 18,
        'h4_size': 13,
        'h5_size': 13,
        'h6_size': 12,
        'p_size': 13,

        'sidebar_is_show_nav_bar': True,
        'sidebar_collapse_style': 'collapsed',
        'sidebar_font_hover_background_color': '#43A047',
        'sidebar_background_style': 'color',
        'sidebar_background_color': '#ffffff',
        'sidebar_font_color': '#181F4C',
        'sidebar_font_hover_color': '#ffffff',
        #
        'separator_color': '#3B9141',
        #        'separator_style': 'style_7',
        #
        #        'button_style': 'style_1',
        #        'is_button_with_icon_text': True,
        #
        #         'body_background_type':'bg_color',
        #         'body_font_family':'Roboto',
        'body_font_color': '#787373',
        #         'body_google_font_family':'Muli',
        #         'is_used_google_font':False,
        #
        #         'list_view_border':'without_border',
        'list_view_is_hover_row': True,
        'list_view_hover_bg_color': '#f2f2f2',
        #         'list_view_even_row_color': '#FFFFFF',
        #         'list_view_odd_row_color': '#ffffff',
        #
        #         'login_page_style': 'style_1',
        #         'login_page_background_type': 'bg_color',
        #         'login_page_box_color':False,
        #
        #         'modal_popup_style':'style_1',
        'loading_style': 'style_1',
        'progress_style': 'style_1',
        'progress_height': '4px',
        'progress_color': '#43A047',
    },
    'color_7_2': {
        'primary_color': '#43A047',
        'primary_hover': '#3B9141',
        'primary_active': '#3B9141',
        'secondary_color': '#e2e4e6',
        'secondary_hover': '#e2e4e6',
        'secondary_active': '#e2e4e6',
        #        'header_background_color': '#ffffff',
        #        'body_background_color': '#ffffff',
        #        'header_font_color': '#a1a1a1',
        'header_hover_color': '#43A047',
        'header_active_color': '#43A047',
        #        'h1_color': '#4E4E4E',
        #        'h2_color': '#4E4E4E',
        #        'h3_color': '#4E4E4E',
        #        'h4_color': '#4E4E4E',
        #        'h5_color': '#4E4E4E',
        #        'h6_color': '#4E4E4E',
        #        'p_color': '#4E4E4E',
        'h1_size': 28,
        'h2_size': 17,
        'h3_size': 18,
        'h4_size': 13,
        'h5_size': 13,
        'h6_size': 12,
        'p_size': 13,

        'sidebar_is_show_nav_bar': True,
        'sidebar_collapse_style': 'expanded',
        'sidebar_background_color': '#ffffff',
        'sidebar_background_style': 'color',
        'sidebar_font_color': '#181F4C',
        'sidebar_font_hover_color': '#ffffff',
        'sidebar_font_hover_background_color': '#3B9141',

        #
        #          'button_style': 'style_2',
        #         'is_button_with_icon_text': True,
        #         'is_button_with_box_shadow': True,
        #
        #        'separator_style': 'style_7',
        'separator_color': '#3B9141',
        #
        #        'body_background_type':'bg_color',
        #        'body_font_family':'Roboto',
        'body_font_color': '#787373',
        #        'body_google_font_family':'Muli',
        #        'is_used_google_font':False,
        #
        #        'list_view_border':'without_border',
        'list_view_is_hover_row': True,
        'list_view_hover_bg_color': '#f2f2f2',
        #        'list_view_even_row_color': '#FFFFFF',
        #        'list_view_odd_row_color': '#ffffff',
        #
        #        'login_page_style': 'style_1',
        #        'login_page_background_type': 'bg_color',
        #        'login_page_box_color':False,
        #
        #
        #        'modal_popup_style':'style_1'
        'loading_style': 'style_4',
        'progress_style': 'style_1',
        'progress_height': '4px',
        'progress_color': '#43A047',
    },
    'color_7_3': {
        'primary_color': '#43A047',
        'primary_hover': '#3B9141',
        'primary_active': '#3B9141',
        'secondary_color': '#e2e4e6',
        'secondary_hover': '#e2e4e6',
        'secondary_active': '#e2e4e6',
        #        'header_background_color': '#ffffff',
        #        'body_background_color': '#ffffff',
        #        'header_font_color': '#a1a1a1',
        'header_hover_color': '#43A047',
        'header_active_color': '#43A047',
        #        'h1_color': '#4E4E4E',
        #        'h2_color': '#4E4E4E',
        #        'h3_color': '#4E4E4E',
        #        'h4_color': '#4E4E4E',
        #        'h5_color': '#4E4E4E',
        #        'h6_color': '#4E4E4E',
        #        'p_color': '#4E4E4E',
        'h1_size': 28,
        'h2_size': 17,
        'h3_size': 18,
        'h4_size': 13,
        'h5_size': 13,
        'h6_size': 12,
        'p_size': 13,
        #
        'sidebar_is_show_nav_bar': True,
        'sidebar_collapse_style': 'collapsed',
        #        'sidebar_background_color': '#ffffff',
        'sidebar_background_style': 'image',
        'sidebar_font_color': '#181F4C',
        'sidebar_font_hover_color': '#43A047',
        'sidebar_font_hover_background_color': '#fafafa',

        #
        #         'button_style': 'style_1',
        #         'is_button_with_icon_text': True,
        #
        #        'separator_style': 'style_7',
        'separator_color': '#3B9141',
        #
        #        'body_background_type':'bg_color',
        #        'body_font_family':'Roboto',
        'body_font_color': '#787373',
        #        'body_google_font_family':'Muli',
        #        'is_used_google_font':False,
        #
        #        'list_view_border':'without_border',
        'list_view_is_hover_row': True,
        'list_view_hover_bg_color': '#f2f2f2',
        #        'list_view_even_row_color': '#FFFFFF',
        #        'list_view_odd_row_color': '#ffffff',
        #
        #        'login_page_style': 'style_1',
        #        'login_page_background_type': 'bg_color',
        #        'login_page_box_color':False,
        #
        #
        #        'modal_popup_style':'style_1'
        'loading_style': 'style_9',
        'progress_style': 'style_1',
        'progress_height': '4px',
        'progress_color': '#43A047',
    },
}
# dict_theme_color= {
#
#     'color_1':{
#        'primary_color': '#5c77ff',
#        'primary_hover': '#004ccb',
#        'primary_active': '#004ccb',
#        'secondary_color': '#e2e4e6',
#        'secondary_hover': '#e2e4e6',
#        'secondary_active': '#e2e4e6',
#        'header_background_color': '#ffffff',
#        'header_font_color': '#a1a1a1',
#        'header_hover_color':'#ffffff',
#        'header_active_color':'#ffffff',
#        'h1_color': '#4E4E4E',
#        'h2_color': '#4E4E4E',
#        'h3_color': '#4E4E4E',
#        'h4_color': '#4E4E4E',
#        'h5_color': '#4E4E4E',
#        'h6_color': '#4E4E4E',
#        'p_color': '#4E4E4E',
#        'h1_size': 28,
#        'h2_size': 17,
#        'h3_size': 18,
#        'h4_size': 20,
#        'h5_size': 13,
#        'h6_size': 12 ,
#        'p_size': 13,
#        'sidebar_background_color': '#5c77ff',
#         'sidebar_font_color': '#ffffff',
#        'sidebar_font_hover_color': '#ffffff',
#        'sidebar_font_hover_background_color': '#5c85ff',
#        'separator_color': '#004ccb',
#
#      },
#
#
#
#     'color_2':{
#        'primary_color': '#ff9800',
#        'primary_hover': '#F29107',
#        'primary_active': '#008ba3',
#        'secondary_color': '#e2e4e6',
#        'secondary_hover': '#e2e4e6',
#        'secondary_active': '#e2e4e6',
#        'header_background_color': '#ffffff',
#        'header_font_color': '#959595',
#        'header_hover_color':'#ffffff',
#        'header_active_color':'#ffffff',
#        'h1_color': '#4E4E4E',
#        'h2_color': '#4E4E4E',
#        'h3_color': '#4E4E4E',
#        'h4_color': '#4E4E4E',
#        'h5_color': '#4E4E4E',
#        'h6_color': '#4E4E4E',
#        'p_color': '#4E4E4E',
#        'h1_size': 28,
#        'h2_size': 17,
#        'h3_size': 18,
#        'h4_size': 20,
#        'h5_size': 13,
#        'h6_size': 12 ,
#        'p_size': 13,
#        'body_font_color': '#4E4E4E',
#        'body_background_color': '#F9F9F9',
#        'sidebar_background_color': '#00bcd4',
#         'sidebar_font_color': '#5a5858',
#        'sidebar_font_hover_color': '#ffffff',
#        'sidebar_font_hover_background_color': '#05a3b8',
#        'separator_color': '#008ba3',
#
#      },
#     'color_3':  {
#       'primary_color': '#ff5722',
#        'primary_hover': '#dc4918',
#        'primary_active': '#dc4918',
#        'secondary_color': '#e2e4e6',
#        'secondary_hover': '#e2e4e6',
#        'secondary_active': '#e2e4e6',
#        'header_background_color': '#ffffff',
#        'header_font_color': '#959595',
#        'header_hover_color':'#ffffff',
#        'header_active_color':'#ffffff',
#        'h1_color': '#4E4E4E',
#        'h2_color': '#4E4E4E',
#        'h3_color': '#4E4E4E',
#        'h4_color': '#4E4E4E',
#        'h5_color': '#4E4E4E',
#        'h6_color': '#4E4E4E',
#        'p_color': '#4E4E4E',
#        'h1_size': 28,
#        'h2_size': 17,
#        'h3_size': 18,
#        'h4_size': 20,
#        'h5_size': 13,
#        'h6_size': 12 ,
#        'p_size': 13,
#        'body_font_color': '#4E4E4E',
#        'body_background_color': '#F9F9F9',
#         'sidebar_font_color': '#ffffff',
#        'sidebar_font_hover_color': '#ffffff',
#        'sidebar_font_hover_background_color': '#dc4918',
#         'sidebar_background_color': '#c41c00',
#        'separator_color': '#c41c00',
#
#
#      } ,
#      'color_4':  {
#       'primary_color': '#7B6056',
#        'primary_hover': '#087f23',
#        'primary_active': '#087f23',
#        'secondary_color': '#e2e4e6',
#        'secondary_hover': '#e2e4e6',
#        'secondary_active': '#e2e4e6',
#        'header_background_color': '#ffffff',
#        'header_font_color': '#959595',
#        'header_hover_color':'#ffffff',
#        'header_active_color':'#ffffff',
#        'h1_color': '#4E4E4E',
#        'h2_color': '#4E4E4E',
#        'h3_color': '#4E4E4E',
#        'h4_color': '#4E4E4E',
#        'h5_color': '#4E4E4E',
#        'h6_color': '#4E4E4E',
#        'p_color': '#4E4E4E',
#        'h1_size': 28,
#        'h2_size': 17,
#        'h3_size': 18,
#        'h4_size': 20,
#        'h5_size': 13,
#        'h6_size': 12 ,
#        'p_size': 13,
#        'body_font_color': '#4E4E4E',
#        'body_background_color': '#F9F9F9',
#         'sidebar_background_color': '#4caf50',
#          'sidebar_font_color': '#ffffff',
#        'sidebar_font_hover_color': '#ffffff',
#        'sidebar_font_hover_background_color': '#087f23',
#        'separator_color': '#087f23',
#
#
#      },
#
#  'color_5':  {
#       'primary_color': '#ff9800',
#        'primary_hover': '#56343C',
#        'primary_active': '#c66900',
#        'secondary_color': '#e2e4e6',
#        'secondary_hover': '#e2e4e6',
#        'secondary_active': '#e2e4e6',
#        'header_background_color': '#ffffff',
#        'header_font_color': '#959595',
#        'header_hover_color':'#ffffff',
#        'header_active_color':'#ffffff',
#        'h1_color': '#4E4E4E',
#        'h2_color': '#4E4E4E',
#        'h3_color': '#4E4E4E',
#        'h4_color': '#4E4E4E',
#        'h5_color': '#4E4E4E',
#        'h6_color': '#4E4E4E',
#        'p_color': '#4E4E4E',
#        'h1_size': 28,
#        'h2_size': 17,
#        'h3_size': 18,
#        'h4_size': 20,
#        'h5_size': 13,
#        'h6_size': 12 ,
#        'p_size': 13,
#        'body_font_color': '#4E4E4E',
#        'body_background_color': '#F9F9F9',
#         'sidebar_background_color': '#ff9800',
#          'sidebar_font_color': '#5a5858',
#        'sidebar_font_hover_color': '#ffffff',
#        'sidebar_font_hover_background_color': '#c66900',
#        'separator_color': '#c66900',
#
#
#      }
#
#
#
#     }
# dict_theme_style = {
#
#     'style_1':{
#
#        'button_style': 'style_1',
#        'separator_style': 'style_7',
#
#
#        'body_background_type':'bg_color',
#        'is_button_with_icon_text': True,
#         'body_font_family':'Roboto',
#         'body_google_font_family':'Muli',
#         'is_used_google_font':False,
#         'list_view_border':'without_border',
#         'list_view_is_hover_row': True,
#         'list_view_hover_bg_color':'#eaeaea',
#         'list_view_even_row_color': '#FFFFFF',
#         'list_view_odd_row_color': '#ffffff',
#         'login_page_style': 'style_0',
#         'login_page_background_type': 'bg_color',
#         'login_page_background_color':'#B3FFB8',
#         'login_page_box_color':False,
#         'sidebar_is_show_nav_bar': True,
#         'sidebar_collapse_style':'collapsed',
#          'modal_popup_style':'style_1',
#         'sidebar_background_color': '#ffffff',
#         'sidebar_font_color': '#616161',
#        'sidebar_font_hover_color': '#ffffff',
#       # 'sidebar_font_hover_background_color': ,
#      },
#
#
#
#     'style_2':{
#
#        'button_style': 'style_1',
#        'separator_style': 'style_7',
#
#        'body_background_type':'bg_color',
#        'is_button_with_icon_text': True,
#
#        'body_font_family':'Roboto',
#        'body_google_font_family':'Muli',
#
#        'is_used_google_font':False,
#
#        'list_view_border':'without_border',
#        'list_view_is_hover_row': True,
#        'list_view_hover_bg_color':'#eaeaea',
#        'list_view_even_row_color': '#FFFFFF',
#        'list_view_odd_row_color': '#ffffff',
#
#        'login_page_style': 'style_0',
#        'login_page_background_type': 'bg_color',
#        'login_page_background_color':'#B3FFB8',
#        'login_page_box_color':False,
#        'sidebar_is_show_nav_bar': True,
#        'sidebar_collapse_style':'expanded',
#        'modal_popup_style':'style_10'
#      },
#     'style_3':  {
#
#         'button_style': 'style_1',
#        'separator_style': 'style_7',
#
#        'body_background_type':'bg_color',
#        'is_button_with_icon_text': True,
#         'body_font_family':'Roboto',
#         'body_google_font_family':'Muli',
#         'is_used_google_font':False,
#         'list_view_border':'without_border',
#         'list_view_is_hover_row': True,
#         'list_view_hover_bg_color':'#eaeaea',
#         'list_view_even_row_color': '#FFFFFF',
#         'list_view_odd_row_color': '#ffffff',
#         'login_page_style': 'style_0',
#         'login_page_background_type': 'bg_color',
#         'login_page_background_color':'#B3FFB8',
#         'login_page_box_color':False,
#         'sidebar_is_show_nav_bar': True,
#         'sidebar_collapse_style':'collapsed',
#          'modal_popup_style':'style_1'
#
#
#      }
#
#
#     }


class ThemeConfigController(http.Controller):

    @http.route('/firebase-messaging-sw.js', type='http', auth="public")
    def sw_http(self):
        if request.env.company and request.env.company.enable_web_push_notification:
            config_obj = request.env.company.config_details

            js = """
            this.addEventListener('install', function(e) {
         e.waitUntil(
           caches.open('video-store').then(function(cache) {
             return cache.addAll([
                 '/sh_backmate_theme_adv/static/index.js'
             ]);
           })
         );
        });
        
        this.addEventListener('fetch', function(e) {
          e.respondWith(
            caches.match(e.request).then(function(response) {
              return response || fetch(e.request);
            })
          );
        });
            importScripts('https://www.gstatic.com/firebasejs/8.4.2/firebase-app.js');
            importScripts('https://www.gstatic.com/firebasejs/8.4.2/firebase-messaging.js');
            var firebaseConfig =
            """ + config_obj + """ ;
            firebase.initializeApp(firebaseConfig);
    
            const messaging = firebase.messaging();
    
            messaging.setBackgroundMessageHandler(function(payload) {
            const notificationTitle = "Background Message Title";
            const notificationOptions = {
                body: payload.notification.body,
                icon:'https://i.pinimg.com/originals/3f/77/56/3f7756330cd418e46e642254a900a507.jpg',
            };
            return self.registration.showNotification(
                notificationTitle,
                notificationOptions,
            );
            });
    
            """
            return http.request.make_response(js, [('Content-Type', 'text/javascript')])
        else:

            js = """
           this.addEventListener('install', function(e) {
         e.waitUntil(
           caches.open('video-store').then(function(cache) {
             return cache.addAll([
                 '/sh_backmate_theme_adv/static/index.js'
             ]);
           })
         );
        });
        
        this.addEventListener('fetch', function(e) {
          e.respondWith(
            caches.match(e.request).then(function(response) {
              return response || fetch(e.request);
            })
          );
        });
    
            """
            return http.request.make_response(js, [('Content-Type', 'text/javascript')])

    @http.route('/web/push_token', type='http', auth="public", csrf=False)
    def getToken(self, **post):
        device_search = request.env['sh.push.notification'].sudo().search(
            [('register_id', '=', post.get('name'))], limit=1)

        if device_search and not request.env.user._is_public() and device_search.user_id != request.env.user.id:
            if request.env.user.has_group('base.group_portal'):
                device_search.write(
                    {'user_id': request.env.user.id, 'user_type': 'portal'})
            elif request.env.user:
                device_search.write(
                    {'user_id': request.env.user.id, 'user_type': 'internal'})

        if not device_search:
            vals = {
                'register_id': post.get('name'),
                'datetime': datetime.now()
            }
            print("\n\n\n\n self.env.user.has_group('base.group_portal')",
                  request.env.user.has_group('base.group_portal'))
            if request.env.user._is_public():
                public_users = request.env['res.users'].sudo()
                public_groups = request.env.ref(
                    "base.group_public", raise_if_not_found=False)
                if public_groups:
                    public_users = public_groups.sudo().with_context(
                        active_test=False).mapped("users")
                    if public_users:
                        vals.update(
                            {'user_id': public_users[0].id, 'user_type': 'public'})
            elif request.env.user.has_group('base.group_portal'):
                vals.update(
                    {'user_id': request.env.user.id, 'user_type': 'portal'})
            elif request.env.user:
                vals.update({'user_id': request.env.user.id,
                             'user_type': 'internal'})

            request.env['sh.push.notification'].sudo().create(vals)

    @http.route('/web/_config', type='json', auth="public")
    def sendConfig(self):

        config_vals = {}
        if request.env.company and request.env.company.enable_web_push_notification:

            config_obj = request.env.company.config_details.replace(" ", "")
            config_obj = request.env.company.config_details.replace("\n", "").replace("\t", "").replace(" ", "").replace("\"", "'").replace('apiKey', '\'apiKey\'').replace('authDomain', '\'authDomain\'').replace(
                'projectId', '\'projectId\'').replace('storageBucket', '\'storageBucket\'').replace('messagingSenderId', '\'messagingSenderId\'').replace('appId', '\'appId\'').replace('measurementId', '\'measurementId\'')

            config_vals['apiKey'] = safe_eval(config_obj)['apiKey']
            config_vals['authDomain'] = safe_eval(config_obj)['authDomain']
            config_vals['projectId'] = safe_eval(config_obj)['projectId']
            config_vals['storageBucket'] = safe_eval(config_obj)[
                'storageBucket']
            config_vals['messagingSenderId'] = safe_eval(config_obj)[
                'messagingSenderId']
            config_vals['appId'] = safe_eval(config_obj)['appId']
            config_vals['measurementId'] = safe_eval(config_obj)[
                'measurementId']

            vals = {
                'vapid': request.env.company.vapid,
                'config':   config_vals
            }
            print(vals)
            json_vals = json.dumps(vals)
            return json_vals

    def _get_manifest_json(self, company):
        if not company:
            company = 1
        pwa_config = http.request.env['sh.pwa.config'].sudo().search(
            [('company_id', '=', int(company))], limit=1)
        vals = {
            "name": "HashMicro-APP",
            "short_name": "HM-APP",
            "scope": "/",
            "start_url": "/web",
            "background_color": "purple",
            "display": "standalone",
        }
        if pwa_config:
            if pwa_config.name:
                vals.update({'name': pwa_config.name})
            if pwa_config.short_name:
                vals.update({'short_name': pwa_config.short_name})
            if pwa_config.theme_color:
                vals.update({'theme_color': pwa_config.theme_color})
            if pwa_config.background_color:
                vals.update({'background_color': pwa_config.background_color})
            if pwa_config.display:
                vals.update({'display': pwa_config.display})
            if pwa_config.orientation:
                vals.update({'orientation': pwa_config.orientation})

            default_icon_list = []
            if pwa_config.icon_small and pwa_config.icon_small_mimetype and pwa_config.icon_small_size:
                default_icon_list.append({
                    'src': '/sh_backmate_theme_adv/pwa_icon_small/'+str(company),
                    'type': pwa_config.icon_small_mimetype,
                    'sizes': pwa_config.icon_small_size
                })
            if pwa_config.icon and pwa_config.icon_mimetype and pwa_config.icon_size:
                default_icon_list.append({
                    'src': '/sh_backmate_theme_adv/pwa_icon/'+str(company),
                    'type': pwa_config.icon_mimetype,
                    'sizes': pwa_config.icon_size
                })

            if len(default_icon_list) == 0:
                default_icon_list = [
                    {
                        "src": "/sh_backmate_theme_adv/static/icon/144x144.png",
                        "sizes": "144x144",
                        "type": "image/png"
                    }
                ]

            vals.update({'icons': default_icon_list})

        return vals

    @http.route('/manifest.json/<string:cid>', type='http', auth="public")
    def manifest_http(self, **post):
        company = post.get('cid')
        return json.dumps(self._get_manifest_json(company))

    # @http.route('/sw.js', type='http', auth="public")
    # def sw_http(self):
    #     js = """
    #     this.addEventListener('install', function(e) {
    #      e.waitUntil(
    #        caches.open('video-store').then(function(cache) {
    #          return cache.addAll([
    #              '/sh_backmate_theme_adv/static/index.js'
    #          ]);
    #        })
    #      );
    #     });

    #     this.addEventListener('fetch', function(e) {
    #       e.respondWith(
    #         caches.match(e.request).then(function(response) {
    #           return response || fetch(e.request);
    #         })
    #       );
    #     });
    #     """
    #     return http.request.make_response(js, [('Content-Type', 'text/javascript')])

    def get_icon(self, field_icon, company):
        pwa_config = http.request.env['sh.pwa.config'].sudo().search(
            [('company_id', '=', int(company))], limit=1)
        if pwa_config:
            icon = pwa_config.icon
            if field_icon == 'icon_small':
                icon = pwa_config.icon_small

#             icon = getattr(pwa_config, field_icon)
            icon_mimetype = getattr(pwa_config, field_icon + '_mimetype')
            if icon:
                icon = BytesIO(base64.b64decode(icon))
            return http.request.make_response(
                icon.read(), [('Content-Type', icon_mimetype)])

    @http.route('/sh_backmate_theme_adv/pwa_icon/<string:cid>', type='http', auth="none")
    def icon_small(self, **post):
        company = post.get('cid')
        return self.get_icon('icon', company)

    @http.route('/sh_backmate_theme_adv/pwa_icon_small/<string:cid>', type='http', auth="none")
    def icon(self, **post):
        company = post.get('cid')
        return self.get_icon('icon_small', company)

    @http.route('/iphone.json/<string:cid>', type='http', auth="public")
    def iphone_http(self, **post):
        company = post.get('cid')
        pwa_config = http.request.env['sh.pwa.config'].sudo().search(
            [('company_id', '=', int(company))], limit=1)
        if pwa_config:
            icon = pwa_config.icon_iphone
            icon_mimetype = getattr(pwa_config, 'icon' + '_mimetype')
            if icon:
                icon = BytesIO(base64.b64decode(icon))
                return http.request.make_response(
                    icon.read(), [('Content-Type', icon_mimetype)])


#     @http.route([
#         '/web/binary/company_name_logo',
#     ], type='http', auth="none", cors="*")
#     def company_logo(self, dbname=None, **kw):
#         print("%%%%%%%%%%ThemeConfigController")
#         imgname = 'logo'
#         imgext = '.png'
#         placeholder = functools.partial(get_resource_path, 'web', 'static', 'src', 'img')
#         uid = None
#         if request.session.db:
#             dbname = request.session.db
#             uid = request.session.uid
#         elif dbname is None:
#             dbname = db_monodb()
#
#         if not uid:
#             uid = odoo.SUPERUSER_ID
#
#         if not dbname:
#             response = http.send_file(placeholder(imgname + imgext))
#         else:
#             try:
#                 # create an empty registry
#                 registry = odoo.modules.registry.Registry(dbname)
#                 with registry.cursor() as cr:
#                     company = int(kw['company']) if kw and kw.get('company') else False
#                     print("&&&&&&&&&&&&7",company)
#                     if company:
#                         cr.execute("""SELECT company_name_logo, write_date
#                                         FROM res_company
#                                        WHERE id = %s
#                                    """, (company,))
# #                     else:
# #                         cr.execute("""SELECT c.company_name_logo, c.write_date
# #                                         FROM res_users u
# #                                    LEFT JOIN res_company c
# #                                           ON c.id = u.company_id
# #                                        WHERE u.id = %s
# #                                    """, (uid,))
#                     row = cr.fetchone()
#                     if row and row[0]:
#                         image_base64 = base64.b64decode(row[0])
#                         image_data = io.BytesIO(image_base64)
#                         mimetype = guess_mimetype(image_base64, default='image/png')
#                         imgext = '.' + mimetype.split('/')[1]
#                         if imgext == '.svg+xml':
#                             imgext = '.svg'
#                         response = http.send_file(image_data, filename=imgname + imgext, mimetype=mimetype, mtime=row[1])
#                     else:
#                         response = http.send_file(placeholder('nologo.png'))
#             except Exception:
#                 response = http.send_file(placeholder(imgname + imgext))
#
#         return response
#


    @http.route('/api/upload/multi', type='http', auth="none", csrf=False)
    def Upload_image(self, **kwargs):

        theme_setting_rec = request.env['sh.back.theme.config.settings'].sudo().search([
            ('id', '=', 1)], limit=1)
        if kwargs.get('body_background_img'):
            body_background_img = base64.b64encode(
                kwargs.get('body_background_img').read())
            if theme_setting_rec:
                theme_setting_rec.write(
                    {'body_background_image': body_background_img})

        print("\n\n\n\n\n kwargs.get('sidebar_background_img')", kwargs)
        if kwargs.get('sidebar_background_img'):
            sidebar_background_img = base64.b64encode(
                kwargs.get('sidebar_background_img').read())
            if theme_setting_rec:
                theme_setting_rec.write(
                    {'sidebar_background_image': sidebar_background_img})

        if kwargs.get('loading_gif'):
            loading_gif = base64.b64encode(kwargs.get('loading_gif').read())
            if theme_setting_rec:
                theme_setting_rec.write({'loading_gif': loading_gif})

        if kwargs.get('login_page_banner_img'):
            login_page_banner_image = base64.b64encode(
                kwargs.get('login_page_banner_img').read())
            if theme_setting_rec:
                theme_setting_rec.write(
                    {'login_page_banner_image': login_page_banner_image})

        if kwargs.get('login_page_icon_img'):
            login_page_icon_img = base64.b64encode(
                kwargs.get('login_page_icon_img').read())
            if theme_setting_rec:
                theme_setting_rec.write(
                    {'login_page_icon_img': login_page_icon_img})
        if kwargs.get('login_page_icon_img_long'):
            login_page_icon_img_long = base64.b64encode(
                kwargs.get('login_page_icon_img_long').read())
            if theme_setting_rec:
                theme_setting_rec.write(
                    {'login_page_icon_img_long': login_page_icon_img_long})

        if kwargs.get('login_page_background_img'):
            login_page_background_image = base64.b64encode(
                kwargs.get('login_page_background_img').read())
            if login_page_background_image:
                theme_setting_rec.write(
                    {'login_page_background_image': login_page_background_image})

        return json.dumps({})

    @http.route('/get_theme_style', type='json', auth="public")
    def get_theme_style(self):
        theme_setting_rec = request.env['sh.back.theme.config.settings'].sudo().search([
            ('id', '=', 1)], limit=1)
        active_color = '1'
        active_style = '1'
        active_pre_color = 'pre_color_1'
        if theme_setting_rec.theme_style:
            active_style = str(theme_setting_rec.theme_style).split('_')[1]
        if theme_setting_rec.theme_color:
            active_color = str(theme_setting_rec.theme_color).split('_')[1]
        if theme_setting_rec.pre_theme_style:
            active_pre_color = theme_setting_rec.pre_theme_style

        data_html = ' <div class="sh_main_div">  <input type="hidden" class="current_active_style" value="style_' + \
            active_style+'"/><input type="hidden" class="current_active_style_pallete"/>'
        data_color = ' <div class="sh_main_div">  <input type="hidden" class="current_active_color" value="color_' + \
            active_color+'"/><input type="hidden" class="current_active_color_pallete"/>'
        data_pre_color = ' <div class="sh_main_div">  <input type="hidden" class="current_active_pre_color" value="' + \
            active_pre_color+'"/><input type="hidden" class="current_active_pre_color_pallete"/>'

        if theme_setting_rec:
            i = 1
            for theme_style in range(3):
                data_html += '<li class="sh_div_plt"><div class="theme_style_box" id="style_' + \
                    str(i)+'"><input type="radio" name="themeStyle"> <span class="circle"></span> <div class="sh_style_box_' + \
                    str(i)+'"></div></label></li>'
                i += 1

            j = 1
            for theme_color in range(7):
                data_color += '<li class="sh_div_plt"><div class="theme_color_box" id="color_' + \
                    str(j)+'"><input type="radio" name="themeColor"> <i class="fa fa-check-circle"></i> <div class="sh_color_box_' + \
                    str(j)+'"></div></label></li>'
                j += 1

            k = 1
            for pre_theme_color in range(3):
                data_pre_color += '<li class="sh_div_plt"><div class="pre_theme_color_box" id="pre_color_' + \
                    str(k)+'"><input type="radio" name="preThemeColor"> <i class="fa fa-check-circle"></i> <div class="sh_pre_color_box_' + \
                    str(k)+'"></div></label></li>'
                k += 1

        return {'data_html': data_html,
                'data_color': data_color,
                'data_pre_color': data_pre_color,
                'primary_color': theme_setting_rec.primary_color,
                'primary_hover': theme_setting_rec.primary_hover,
                'primary_active': theme_setting_rec.primary_active,
                'gradient_color': theme_setting_rec.gradient_color,
                'secondary_color': theme_setting_rec.secondary_color,
                'secondary_hover': theme_setting_rec.secondary_hover,
                'secondary_active': theme_setting_rec.secondary_active,
                'header_background_color': theme_setting_rec.header_background_color,
                'header_font_color': theme_setting_rec.header_font_color,
                'header_hover_color': theme_setting_rec.header_hover_color,
                'header_active_color': theme_setting_rec.header_active_color,
                'body_font_color': theme_setting_rec.body_font_color,
                'body_background_color': theme_setting_rec.body_background_color,
                'body_font_family': theme_setting_rec.body_font_family,
                'body_google_font_family': theme_setting_rec.body_google_font_family,
                'body_background_type': theme_setting_rec.body_background_type,
                'h1_color': theme_setting_rec.h1_color,
                'h2_color': theme_setting_rec.h2_color,
                'h3_color': theme_setting_rec.h3_color,
                'h4_color': theme_setting_rec.h4_color,
                'h5_color': theme_setting_rec.h5_color,
                'h6_color': theme_setting_rec.h6_color,
                'p_color': theme_setting_rec.p_color,
                'h1_size': theme_setting_rec.h1_size,
                'h2_size': theme_setting_rec.h2_size,
                'h3_size': theme_setting_rec.h3_size,
                'h4_size': theme_setting_rec.h4_size,
                'h5_size': theme_setting_rec.h5_size,
                'h6_size': theme_setting_rec.h6_size,
                'p_size': theme_setting_rec.p_size,
                'button_style': theme_setting_rec.button_style,
                'separator_style': theme_setting_rec.separator_style,
                'separator_color': theme_setting_rec.separator_color,
                'icon_style': theme_setting_rec.icon_style,
                'is_button_with_icon_text': theme_setting_rec.is_button_with_icon_text,
                'is_button_with_box_shadow': theme_setting_rec.is_button_with_box_shadow,
                'sidebar_font_color': theme_setting_rec.sidebar_font_color,
                'sidebar_font_hover_color': theme_setting_rec.sidebar_font_hover_color,
                'sidebar_background_style': theme_setting_rec.sidebar_background_style,
                'sidebar_background_color': theme_setting_rec.sidebar_background_color,
                'sidebar_font_hover_background_color': theme_setting_rec.sidebar_font_hover_background_color,
                #                  'sidebar_is_show_navbar':theme_setting_rec.sidebar_is_show_nav_bar,
                'sidebar_collapse_style': theme_setting_rec.sidebar_collapse_style,
                'list_view_border': theme_setting_rec.list_view_border,
                'list_view_even_row_color': theme_setting_rec.list_view_even_row_color,
                'list_view_odd_row_color': theme_setting_rec.list_view_odd_row_color,
                'list_view_is_hover_row': theme_setting_rec.list_view_is_hover_row,
                'list_view_hover_bg_color': theme_setting_rec.list_view_hover_bg_color,
                'login_page_style': theme_setting_rec.login_page_style,
                'login_page_background_type': theme_setting_rec.login_page_background_type,
                'login_page_box_color': theme_setting_rec.login_page_box_color,
                'login_page_background_color': theme_setting_rec.login_page_background_color,
                'is_sticky_form': theme_setting_rec.is_sticky_form,
                'is_sticky_chatter': theme_setting_rec.is_sticky_chatter,
                'is_sticky_list': theme_setting_rec.is_sticky_list,
                'is_sticky_list_inside_form': theme_setting_rec.is_sticky_list_inside_form,
                'modal_popup_style': theme_setting_rec.modal_popup_style,
                'tab_style': theme_setting_rec.tab_style,
                'tab_mobile_style': theme_setting_rec.tab_style_mobile,
                'horizontal_tab_style': theme_setting_rec.horizontal_tab_style,
                'vertical_tab_style': theme_setting_rec.vertical_tab_style,
                'form_element_style': theme_setting_rec.form_element_style,
                'search_style': theme_setting_rec.search_style,
                'breadcrumb_style': theme_setting_rec.breadcrumb_style,
                'chatter_position': theme_setting_rec.chatter_position,
                'loading_style':theme_setting_rec.loading_style,
                'progress_style':theme_setting_rec.progress_style,
                'progress_height':theme_setting_rec.progress_height,
                'progress_color':theme_setting_rec.progress_color,
                }

    @http.route('/update/theme_style', type='json', auth="public")
    def update_theme_style(self, color_id):
        theme_setting_rec = request.env['sh.back.theme.config.settings'].sudo().search([
            ('id', '=', 1)], limit=1)
        theme_style = 'color_' + \
            theme_setting_rec.theme_color.split(
                '_')[1]+'_'+color_id.split('_')[1]

        selected_theme_style_dict = dict_theme_color_style.get(
            theme_style, False)

        if selected_theme_style_dict:
            theme_setting_rec.update(selected_theme_style_dict)
            theme_setting_rec.write(
                {'theme_style': 'style_'+color_id.split('_')[1]})

        return {}

    @http.route('/update/theme_style_color', type='json', auth="public")
    def theme_style_color(self, color_id):
        theme_setting_rec = request.env['sh.back.theme.config.settings'].sudo().search([
            ('id', '=', 1)], limit=1)
        theme_color = 'color_' + \
            color_id.split('_')[1]+'_' + \
            theme_setting_rec.theme_style.split('_')[1]

        selected_theme_style_dict = dict_theme_color_style.get(
            theme_color, False)

        if selected_theme_style_dict:
            theme_setting_rec.update(selected_theme_style_dict)
            theme_setting_rec.write(
                {'theme_color': 'color_'+color_id.split('_')[1]})
        return {}

    @http.route('/update/theme_style_pre_color', type='json', auth="public")
    def theme_style_pre_color(self, pre_color_id):
        theme_setting_rec = request.env['sh.back.theme.config.settings'].sudo().search([
            ('id', '=', 1)], limit=1)
        pre_theme_color = pre_color_id

        selected_theme_style_dict = dict_pre_theme_color_style.get(
            pre_theme_color, False)

        predefined_style_1_back_image = request.env.ref(
            'sh_backmate_theme_adv.sh_back_theme_config_adv_attachment_predefined_theme_1')

        selected_theme_style_dict.update({
            'body_background_image': predefined_style_1_back_image.datas
        })

        if selected_theme_style_dict:
            theme_setting_rec.update(selected_theme_style_dict)
            theme_setting_rec.write({'pre_theme_style': pre_theme_color})
        return {}

    @http.route('/update/theme_color', type='json', auth="public")
    def update_theme_color(self, primary_color_id, primary_hover_id, primary_active_id, gradient_color, secondary_color_id, secondary_hover_id, secondary_active_id,
                           header_background_color, header_font_color, header_hover_color, header_active_color, body_font_color, body_background_color,
                           body_font_family, body_background_type, h1_color, h2_color, h3_color, h4_color, h5_color, h6_color, p_color, h1_size, h2_size, h3_size, h4_size,
                           h5_size, h6_size, p_size, button_style, separator_style, separator_color, icon_style, is_button_with_icon_text, is_button_with_box_shadow,
                           sidebar_font_color, sidebar_font_hover_color, sidebar_background_style, sidebar_background_color, sidebar_font_hover_background_color, sidebar_collapse_style, list_view_border, list_view_even_row_color, list_view_odd_row_color, list_view_is_hover_row,
                           list_view_hover_bg_color, login_page_style, login_page_background_type, login_page_box_color, login_page_background_color,
                           is_sticky_form, is_sticky_chatter, is_sticky_list, is_sticky_list_inside_form, modal_popup_style, body_google_font_family,
                           tab_style, tab_style_mobile, horizontal_tab_style, vertical_tab_style, form_element_style, search_style, breadcrumb_style,chatter_position,loading_style,progress_style,progress_height,progress_color):
        theme_setting_rec = request.env['sh.back.theme.config.settings'].sudo().search([
            ('id', '=', 1)], limit=1)
        is_used_google_font = False
        if body_font_family == 'custom_google_font':
            is_used_google_font = True
        else:
            is_used_google_font = False
            body_google_font_family = 'Muli'

        if theme_setting_rec:
            theme_setting_rec.write({
                                    'is_used_google_font': is_used_google_font,
                                    'body_google_font_family': body_google_font_family,
                                    'primary_color': primary_color_id,
                                    'primary_hover': primary_hover_id,
                                    'primary_active': primary_active_id,
                                    'gradient_color': gradient_color,
                                    'secondary_color': secondary_color_id,
                                    'secondary_hover': secondary_hover_id,
                                    'secondary_active': secondary_active_id,
                                    'header_background_color': header_background_color,
                                    'header_font_color': header_font_color,
                                    'header_hover_color': header_hover_color,
                                    'header_active_color': header_active_color,
                                    'body_font_color': body_font_color,
                                    'body_background_color': body_background_color,
                                    'body_font_family': body_font_family,
                                    'body_background_type': body_background_type,
                                    'h1_color': h1_color,
                                    'h2_color': h2_color,
                                    'h3_color': h3_color,
                                    'h4_color': h4_color,
                                    'h5_color': h5_color,
                                    'h6_color': h6_color,
                                    'p_color': p_color,
                                    'h1_size': h1_size,
                                    'h2_size': h2_size,
                                    'h3_size': h3_size,
                                    'h4_size': h4_size,
                                    'h5_size': h5_size,
                                    'h6_size': h6_size,
                                    'p_size': p_size,
                                    'button_style': button_style,
                                    'separator_style': separator_style,
                                    'separator_color': separator_color,
                                    'icon_style': icon_style,
                                    'is_button_with_icon_text': is_button_with_icon_text,
                                    'is_button_with_box_shadow': is_button_with_box_shadow,
                                    'sidebar_font_color': sidebar_font_color,
                                    'sidebar_font_hover_color': sidebar_font_hover_color,
                                    'sidebar_background_style': sidebar_background_style,
                                    'sidebar_background_color': sidebar_background_color,
                                    'sidebar_font_hover_background_color': sidebar_font_hover_background_color,
                                    #                                      'sidebar_is_show_nav_bar':sidebar_is_show_navbar,
                                    'sidebar_collapse_style': sidebar_collapse_style,
                                    'list_view_border': list_view_border,
                                    'list_view_even_row_color': list_view_even_row_color,
                                    'list_view_odd_row_color': list_view_odd_row_color,
                                    'list_view_is_hover_row': list_view_is_hover_row,
                                    'list_view_hover_bg_color': list_view_hover_bg_color,
                                    'login_page_style': login_page_style,
                                    'login_page_background_type': login_page_background_type,
                                    'login_page_box_color': login_page_box_color,
                                    'login_page_background_color': login_page_background_color,
                                    'is_sticky_form': is_sticky_form,
                                    'is_sticky_chatter': is_sticky_chatter,
                                    'is_sticky_list': is_sticky_list,
                                    'is_sticky_list_inside_form': is_sticky_list_inside_form,
                                    'modal_popup_style': modal_popup_style,
                                    'tab_style': tab_style,
                                    'tab_style_mobile': tab_style_mobile,
                                    'horizontal_tab_style': horizontal_tab_style,
                                    'vertical_tab_style': vertical_tab_style,
                                    'form_element_style': form_element_style,
                                    'search_style': search_style,
                                    'breadcrumb_style': breadcrumb_style,
                                    'chatter_position':chatter_position,
                                    'loading_style':loading_style,
                                    'progress_style':progress_style,
                                    'progress_height':progress_height,
                                    'progress_color':progress_color
                                    })

            return {}
