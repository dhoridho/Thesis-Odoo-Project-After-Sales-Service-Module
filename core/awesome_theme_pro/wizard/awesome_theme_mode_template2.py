# -*- coding: utf-8 -*-

template = """

body.$mode_name {
    
    background-color: $light_background_color !important;
    color: $text_color !important;

    .navigation {
        background: $dark_background_color !important;

        .navigation-menu-tab {
            background: $dark_background_color !important;
            box-shadow: 0 -4px 25px 0 $shadow_color !important;
        }

        .awesome-nav-footer {
            background: $dark_background_color !important;
            border-top: 1px solid $primary_border_color !important;
        }
        
        .navigation-menu-body {
            border-right: 1px solid $primary_border_color !important;
            background: $dark_background_color !important;
        }
    }

    .o_action_manager {
        background: $light_background_color !important;
        .awesome_pop_form  {
            .awesome_pop_form_footer {
                border-top: $primary_border_color !important;
                background-color: $dark_background_color !important;
            }
        }
    }

    .btn-primary {
        background-color: $primary_color !important;
        color: $primary_text_color !important;
        border-color: $primary_border_color !important;
        box-shadow: none !important;

        &:hover {
            color: $primary_text_hover_color !important;
            background-color: $primary_hover_color !important;
            border-color: $primary_border_hover_color !important;
        }
    }

    .btn-secondary {
        color: $secondary_text_color !important;
        background-color: $secondary_color !important;
        border-color: $primary_border_color !important;
        
        &:hover {
            color: $secondary_text_hover_color !important;
            background-color: $secondary_hover_color !important;
            border-color: $secondary_border_hover_color !important;
        }

        &:not(:disabled):not(.disabled).active {
            color: $primary_text_active_color !important;
            background-color: $primary_active_color !important;
            border-color: primary_active_border !important;
        }
    }

    a:not(.btn) {
        color: $link_text_color !important;
        &:hover {
            color: $link_text_hover_color !important;
        }
    }

    // here 
    .awesome_header {
        background: $dark_background_color !important;
        box-shadow: 0px 4px 16px $shadow_color !important;
        border-color: $dark_border_color !important;

        .navigation-toggler {
            background-color: $primary_color !important;
            border: 1px solid $primary_border_color !important;

            a {
                padding: 8px 12px !important;
                color: $primary_text_color !important;
                &:hover {
                    color: $primary_text_hover_color !important;
                    border-color: $primary_border_hover_color !important;
                    background-color: $primary_hover_color !important;
                }
            }
        }

        .avatar {
            border-color: transparent !important;
        }
    }
}

body.$mode_name {
    .awesome_multi_tab_container {
        box-shadow: 0 1px 2px 0 $shadow_color !important;

        .awesome_multi_tab {
            background: $dark_background_color !important;

            .awesome_tab_scroller {
                .awesome_page_items {
                    background: $dark_background_color !important;

                    li{
                        border-right: 1px solid $primary_border_color !important;
                        &:hover {
                            background-color: $dark_background_color !important;
                        }
                    }
                }
            }

            .awesome_tab_control {
                border-right: 1px solid $primary_border_color !important;
                border-left: 1px solid $primary_border_color !important;

                &:hover {
                    background-color: $light_background_color !important;
                }
            }

            .awesome_multi_tab_active {
                background-color: $light_background_color !important;
            }

            .awesome_icon_prev {
                border-right: 1px solid $primary_border_color !important;
            }

            .awesome_icon_next {
                border-right: 1px solid $primary_border_color !important;
                border-left: 1px solid $primary_border_color !important;
            }

            .awesome_icon_down {
                border-left: none;
            }
        }
    }
}

body.$mode_name {
    .breadcrumb {
        li {
            a {
                color: $primary_text_color !important;
                &:hover {
                    color: $primary_text_hover_color !important
                }
            }

            .breadcrumb-item.active {
                color: $primary_text_active_color !important
            }
        }
    }
}

body.$mode_name {

    .alert {
        color: $primary_text_color !important;

        hr {
            border-color: $primary_border_color !important;
        }

        .close:focus, .close:hover {
            opacity: .2;
            color: inherit
        }
    }

    .custom-control-label::before {
        border: 1px solid $primary_border_color !important;
        background-color: $dark_background_color !important;
    }

    .custom-control-input:disabled~.custom-control-label::before {
        background-color: $light_background_color !important;
        border: 1px solid $primary_border_color !important
    }

    .custom-radio {
        .custom-control-label{
            &::after {
                background: $light_background_color !important;
                border-color: $primary_border_color !important;
                color: $primary_text_color !important;
            }
        }
    }

    .form-control {
        color: $primary_text_color !important;
        opacity: 1;
        background-color: $dark_background_color !important;
        border: 1px solid $primary_border_color !important;

        &:focus {
            color: $primary_text_color !important;
            background-color: $dark_background_color !important;
            border-color: $primary_border_color !important;
        }
    }

    .custom-select {
        border-color: $primary_border_color !important;
        color: $primary_text_color !important;
        background: $dark_background_color !important;
        border: 1px solid $primary_border_color !important;
    }

    .custom-file-label {
        background-color: inherit !important;
        border-color: $primary_border_color !important;
        color: inherit !important
    }

    .custom-range::-webkit-slider-runnable-track {
        background-color: $primary_border_color !important
    }

    hr {
        border-color: $primary_border_color !important
    }

    .o_dropdown {
        &.show, &.hover {
            .o_dropdown_toggler_btn {
                color: $primary_text_color !important;
            }
        }
    }

    .dropdown-menu {
        box-shadow: 0 6px 12px $shadow_color !important;
        color: $primary_text_color !important;
        background-color: $dark_background_color !important;
        border: 1px solid $primary_border_color !important;

        .dropdown-item {
            color: $text_color !important;

            &:focus, &:hover {
                color: $link_text_hover_color !important;
                background-color: $link_hover_color !important;
            }
        }

        .dropdown-item-text {
            color: $primary_text_color !important;
        }

        .o_menu_item > .dropdown-item:hover {
            color: $primary_text_color;
            background-color: $dark_background_color !important;
        }
    } 

    .dropdown-divider {
        border-top-color: $dark_background_color !important
    }

    .list-group-item {
        background: 0 0;
        background-color: $dark_background_color !important;
    }

    .list-group-item-action {
        color: inherit !important
    }

    .card {
        background-color: $dark_background_color !important;
        box-shadow: -8px 12px 18px 0 $dark_background_color !important;

        .card-header {
            border-bottom: none !important;
        }

        .card-footer {
            border-top-color: $dark_background_color !important
        }
    }

    .avatar{
        &:before {
            border-color: $dark_background_color !important
        }

        .avatar-title {
            background-color: $dark_background_color !important
        }
    }

    .img-thumbnail {
        border-color: $dark_background_color !important;
        background-color: $dark_background_color !important
    }

    .progress {
        background-color: $dark_background_color !important
    }

    .timeline {
        .timeline-item::before {
            background: $dark_background_color !important
        }
    }
}

body.$mode_name {

    .select2-container--default {
        .select2-selection--multiple {
            background-color: $dark_background_color !important;
            border: 1px solid $primary_border_color !important;

            .select2-selection__choice {
                background-color: $dark_background_color !important;
                border: 1px solid $dark_background_color !important;
            }
        }

        .select2-selection--single {
            background-color: inherit !important;
        }

        .select2-search--dropdown .select2-search__field {
            border: 1px solid $primary_border_color !important;
            background: $dark_background_color !important;
            color: $primary_text_color !important;
        }

        .select2-selection--single .select2-selection__rendered {
            color: inherit !important
        }

        .select2-results__option[aria-selected=true] {
            background-color: $dark_background_color !important;
            color: inherit !important
        }

        .select2-results__option--highlighted[aria-selected] {
            background-color: $dark_background_color !important;
        }
    }

    .select2{
        &.select2-container {
            .select2-selection {
                background-color: $dark_background_color !important;
                border: 1px solid $primary_border_color !important;
            }
    
            .select2-search--inline .select2-search__field {
                color: inherit !important
            }
        }
    }

    .select2-dropdown {
        box-shadow: 0 6px 12px $shadow_color !important;
        color: $primary_text_color !important;
        background-color: $dark_background_color !important;
        border: 1px solid $primary_border_color !important;
    }
}

body.$mode_name{
    .daterangepicker {
        background-color: $dark_background_color !important;
        border-color: $dark_background_color !important;

        select {
            background-color: inherit !important;
            color: inherit !important;
            border-color: $dark_background_color !important
        }

        &:after, &:before {
            border-bottom-color: $dark_background_color !important
        }

        td.in-range {
            background-color: $dark_background_color !important;
            color: inherit !important
        }

        td.end-date {
            color: $primary_text_color !important;
            background-color: $dark_background_color !important
        }

        .drp-buttons {
            border-top-color: $dark_background_color !important;

            .btn.btn-default {
                color: inherit !important
            }
        }

        td.off, td.off.end-date, td.off.start-date {
            background-color: inherit !important;
            color: $dark_background_color !important
        }

        td {
            &.off.in-range {
                color: $primary_text_color !important;
                background-color: $dark_background_color !important;
            }

            &.available:hover {
                background-color: $dark_background_color !important;
                border-color: transparent !important;
                color: inherit !important;
            }
        }

        th {
            &.available:hover {
                background-color: $dark_background_color;
                border-color: transparent !important;
                color: inherit !important;
            }
        }

        .daterangepicker:after {
            border-bottom-color: $dark_background_color !important;
        }

        .ranges li:hover {
            background-color: $dark_background_color !important;
        }

        .popover.clockpicker-popover {
            overflow: hidden !important;
            border: 1px solid $dark_background_color !important;

            &.popover-title {
                background-color: $dark_background_color !important;
                color: inherit !important
            }

            &.popover-content {
                background-color: $dark_background_color !important
            }
        }

        .calendar-table {
            border: 0px solid $primary_border_color !important;
            background-color: $dark_background_color !important;
            color: $primary_text_color !important;

            .next span, .prev span {
                border-color: $primary_border_color !important
            }
        }
    }

    .popover{
        &.clockpicker-popover {
            .clockpicker-plate {
                -webkit-filter: drop-shadow(0 1px 3px $shadow_color) !important;
                filter: drop-shadow(0 1px 3px $shadow_color) !important;
                background-color: $dark_background_color !important;
                border: 1px solid $primary_border_color !important;

                .clockpicker-tick {
                    color: inherit !important
                }

                .clockpicker-canvas-bg {
                    fill: $dark_background_color !important
                }
            }
        }
    }
}

body.$mode_name {

    .nav-pills .nav-link.active, .nav-pills .show > .nav-link {
        color: $primary_text_color !important;
        background-color: $dark_background_color !important;
        border: 1px solid $dark_background_color !important;
    }

    .nav-tabs {
        border-bottom-color: $light_border_color !important;

        .nav-link{
            &:focus, &:hover {
                border-color: $light_border_color !important;
                background: $light_background_color !important;
                border-bottom-color: $light_background_color !important;
                color: $link_text_hover_color !important;
            }
        }
    
        .nav-link{
            .nav-link, &.active {
                color: $link_text_color !important;
                background: $light_background_color !important;
                border-color: $light_border_color !important;
                border-bottom-color: $light_border_color !important;
            }
        }
    }
}


body.$mode_name {
    .figure-caption {
        color: inherit !important
    }

    .btn-link {
        color: inherit !important
    }
}


body.$mode_name {
    .nicescroll-cursors {
        background-color: $primary_border_color !important
    }
}

body.$mode_name {

    .table td, .table th {
        border-color: $primary_border_color !important
    }
    
    .table-striped {
        tbody tr:nth-of-type(even) {
            background-color: $table_odd_row_color !important;
        }
    }

    .table-hover {
        tbody {
            tr:hover {
                background-color: $table_row_hover_color !important;
                color: $text_color !important;
            }
        }
    }
}

body.$mode_name {
    .input-group-text {
        background-color: $dark_background_color !important;
        border: 1px solid $primary_border_color !important;
    }
}

body.$mode_name .btn.btn-outline-light {
    border: 1px solid $primary_border_color !important;
    color: #c7c7c7 !important
}

body.$mode_name .btn.btn-outline-light:hover {
    background: 0 0 !important;
    color: #d6d6d6 !important;
    border: 1px solid $primary_border_color !important
}

body.$mode_name .modal-content {
    background-color: $dark_background_color !important
}

body.$mode_name .modal-content .modal-header {
    border-bottom-color: $light_border_color !important;
    background-color: $light_background_color !important
}

body.$mode_name .modal-content .modal-header .close {
    text-shadow: none !important;
    opacity: 1 !important;
    color: inherit !important;
    background-color: transparent !important;
}

body.$mode_name .modal-content .modal-footer {
    border-top-color: $light_border_color !important;
    background-color: $light_background_color !important;
}

body.$mode_name .popover {
    background-color: $primary_border_color !important
}

body.$mode_name .popover .popover-header {
    background-color: $dark_background_color !important;
    border-color: transparent !important
}

body.$mode_name .popover .popover-body {
    color: inherit !important 
}

body.$mode_name .popover .popover-navigation {
    border-top-color: $dark_background_color !important
}

body.$mode_name .bs-popover-auto[x-placement^=top]>.arrow::after,
body.$mode_name .bs-popover-top>.arrow::after {
    border-top-color: $primary_border_color !important
}

body.$mode_name .bs-popover-auto[x-placement^=right]>.arrow::after,
body.$mode_name .bs-popover-right>.arrow::after {
    border-right-color: $primary_border_color !important
}

body.$mode_name .bs-popover-auto[x-placement^=bottom]>.arrow::after,
body.$mode_name .bs-popover-bottom>.arrow::after {
    border-bottom-color: $primary_border_color !important
}

body.$mode_name .bs-popover-auto[x-placement^=left]>.arrow::after,
body.$mode_name .bs-popover-left>.arrow::after {
    border-left-color: $primary_border_color !important
}

body.$mode_name {
    .page-item{
        &.disabled {
            .page-link {
                color: #ced4da !important;
                background-color: $dark_background_color !important;
                border-color: $primary_border_color !important;
            }
        }

        .page-link {
            background-color: inherit !important;
            color: inherit !important;
            border-color: $dark_background_color !important;
    
            &:hover {
                color: $primary_text_color !important;
                background-color: $dark_background_color !important;
                color: $primary_text_color !important;
            }
        }
    }
}


body.$mode_name {
    .nav {
        a.nav-link:not(.active) {
            color: $dark_background_color !important
        }

        a.nav-link:not(.active):active, a.nav-link:not(.active):hover {
            background-color: $dark_background_color !important
        }
    }
}


@media (min-width:1200px) {
    body.$mode_name{
        &.navigation-toggle-one{
            &.navigation-show {
                .navigation {
                    .navigation-menu-body {
                        background-color: $dark_background_color !important;
                    }
                }
            }
        }
    }
}

@media (max-width:414px) {
    body.$mode_name {
        .nav {
            li.nav-item {
                border-bottom-color: $dark_background_color !important;
                color: $primary_text_color !important;
            }
        }
    }
}

body.$mode_name {
    .o_Chatter {
        background-color: $dark_background_color !important;
        border-color: $primary_border_color !important;

        .o_Message{
            &.o-not-discussion {
                background-color: $dark_background_color !important;
            }
        }

        .o_MessageList_separatorLabel {
            background-color: transparent !important;
        }

        .o_MessageList {
            background-color: $light_background_color !important;
        }

        .o_Message.o-not-discussion {
            background-color: $dark_background_color !important;
            border-bottom: 1px solid $dark_background_color !important;
        }
    }
}

body.$mode_name {
    .o_action_manager {
        background-color: $light_background_color !important;
    }
}

body.$mode_name {
    .h1, .h2, .h3, .h4, .h5, .h6 {
        margin-bottom: none !important;
        font-weight: 400 !important;
        color: $primary_text_color !important;
    }
}

body.$mode_name {
    .awesome_footer {
        color: $primary_text_color !important;
        background-color: $dark_background_color !important;
        border-top: 1px solid $light_border_color !important;
        box-shadow: -1px 2px 15px 0 $shadow_color !important;
        
        .o_pager .o_pager_counter {
            color:$primary_text_color !important;
        }
    }
}

body.$mode_name {

    .oe_button_box {
        box-shadow: inset 0 -1px 0 $primary_border_color !important;
    }
    
    .o_form_view {
        background-color: $dark_background_color;

        .o_form_sheet_bg>.o_form_sheet {
            min-width: initial;
            border: 1px solid $dark_background_color !important;
            background: transparent !important;
            box-shadow: 2px 1px 20px 0px $shadow_color !important;
        }

        .oe_button_box.o_not_full .oe_stat_button {
            border-left: 1px solid $primary_border_color !important;
        }
        
        .o_list_table {
            border-top: 1px solid $light_border_color;
        }
    }

    &.o_required_modifier.o_input .o_input {
        background-color: $dark_background_color !important;
    }

    .o_input, .single-line {
        background: $light_background_color !important;
        border-color: $light_border_color !important;
        color: $text_color !important;
    }

    .text-divider:after {
        background-color: $primary_border_color !important
    }

    input {
        &::-webkit-input-placeholder {
            color: rgba(255, 255, 255, .5) !important
        }

        &::-moz-placeholder {
            color: rgba(255, 255, 255, .5) !important
        }

        &::-ms-input-placeholder {
            color: rgba(255, 255, 255, .5) !important
        }

        &::placeholder {
            color: rgba(255, 255, 255, .5) !important
        }
    }

    .border {
        border-color: $primary_border_color !important
    }

    .border-right {
        border-left-color: $primary_border_color !important;
        border-right-color: $primary_border_color !important
    }

    .border-left {
        border-left-color: $primary_border_color !important;
        border-right-color: $primary_border_color !important
    }

    .border-bottom {
        border-bottom-color: $primary_border_color !important
    }

    .border-top {
        border-top-color: $primary_border_color !important
    }
}

body.$mode_name {
    .card {
        background: $dark_background_color !important;
    }
}

body.$mode_name .input-group-text {
    background-color: $dark_background_color !important;
    border: 1px solid $primary_border_color !important;

    &:focus {
        outline: none !important;
    }
}

body.$mode_name {
    .ui-autocomplete {
        box-shadow: 0 6px 12px $shadow_color !important;
        color: $primary_text_color !important;
        background-color: $dark_background_color !important;
        border: 1px solid $primary_border_color !important;

        .ui-menu-item:hover, .ui-menu-item>a:hover {
            color: $primary_text_color !important;
            background-color: $dark_background_color !important;
        }

        .ui-menu-item {
            > a.ui-state-active {
                background-color: $dark_background_color !important;
            }
        }
    }
}

//  searchview
body.$mode_name {

    .o_searchview {
        background: $light_background_color !important;
        color: $text_color !important;
        border-color: $light_border_color !important;

        .o_searchview_facet {
            border: 1px solid $primary_border_color !important;
            background:  $dark_background_color !important;
            .o_searchview_facet_label {
                background-color:  $dark_background_color !important;
            }
        }
        
        .o_searchview_autocomplete {
            li.o-selection-focus {
                background-color: $link_hover_color !important;
            }
            
            .ui-menu-item.ui-state-focus {
                background-color: $link_active_color !important;
            }
        }

        .o_searchview_input_container {
            .o_searchview_input {
                background: $light_background_color !important;
                color: $text_color !important;
            }
        }

        .o_searchview_autocomplete {
            li {
                &.o_selection_focus {
                    background-color: $link_active_color !important;
                }
            }
        }
    }
}

body.$mode_name {
    .o_kanban_view {
        .o_kanban_record {
            background-color: $dark_background_color !important;
            box-shadow: -8px 12px 18px 0 $dark_background_color !important;
            border-color: $dark_border_color !important;
            color: $primary_text_color;

            .o_dropdown_kanban.show {
                .dropdown-toggle {
                    background: $dark_background_color !important;
                    border-color: $primary_border_color !important;
                }
            }
        }

        .o_kanban_quick_create {
            border: 1px solid $dark_background_color !important;
            background-color: $dark_background_color !important;
        }
    }

    .oe_kanban_card {
        .o_dropdown_kanban{
            &.show {
                .dropdown-toggle {
                    background: $dark_background_color !important;
                    border-color: $primary_border_color !important;
                }
            }
        }
    }
}


body.$mode_name {
    .table {
        color: $primary_text_color !important;
    }

    .o_list_view {
        .o_list_table {
            background-color: transparent !important;
            thead {
                th:focus-within {
                    background-color: transparent !important;
                }

                color: $primary_text_color !important;
                border-bottom: none !important;
                background-color: $dark_background_color !important;
                &>tr>th:nth-of-type(1) {
                    border-left: none !important;
                }
            }

            tbody{
                &.o_keyboard_navigation {
                    td:focus-within {
                        background-color: transparent !important;
                    }
                }
            }

            tfoot {
                background-color: $dark_background_color !important;
            }

            tr:focus-within, th:focus-within {
                background-color: transparent !important;
            }

            &.table-striped tr:focus-within{
                background-color: transparent !important;
            }

            .thead, thead tr:nth-child(1) th {
                background: $dark_background_color !important;
            }

            tfoot tr:nth-child(1) td {
                background-color: $dark_background_color !important;
            }
        }
    }
}

body.$mode_name {
    .oe_button_box {
        box-shadow: inset 0 -1px 0 $dark_background_color !important;
    }
}

body.$mode_name {
    .o_form_view {
        .oe_button_box.o_not_full {
            .oe_stat_button {
                border-left: 1px solid $dark_background_color !important;
                padding-left: 5px !important;
            }
        }
    }
}

body.$mode_name {
    .custom-control-input:not(:disabled):active~.custom-control-label::before {
        color: #c7c7c7 !important;
        background-color: transparent !important;
        border: 1px solid $dark_background_color !important;
    }
}

body.$mode_name {
    .card-body {
        background: $dark_background_color !important;
        color: #c3c3c3 !important;
    }
}

body.$mode_name .o_list_view tbody>tr.o_group_header,
body.$mode_name .o_list_view tbody>tr.o_group_header:focus-within {
    background-image: linear-gradient(to bottom, $dark_background_color, $dark_background_color) !important;
}

body.$mode_name {
    .custom-control-input{
        &:checked~.custom-control-label::before {
            background-color: $light_background_color !important;
        }
    }
}

body.$mode_name {
    .bootstrap-datetimepicker-widget{
        &.dropdown-menu{
            &.bottom::after {
                border-bottom: 10px solid $dark_background_color !important;
            }

            &.top:after {
                border-top: 6px solid $dark_background_color !important;
            }
        }
    }
}

body.$mode_name {
    .o_kanban_view {

        &.o_kanban_grouped {
            background-color: $dark_background_color !important;
        }
        
        .o_column_quick_create {
            .o_quick_create_unfolded {
                padding: 8px 8px !important;
                width: 240px !important;
                height: 100% !important;
                border: none !important;
                box-shadow: 0 0 20px -10px !important;
                background-color: $dark_background_color !important;
            }
        }
    }
}

body.$mode_name {
    .o_mail_preview {
        background-color: $dark_background_color !important;
        color: $primary_text_color !important;

        &.o_systray_activity:hover {
            background-color: $dark_background_color !important;
        }

        &:not(:last-child) {
            border-bottom: 1px solid $dark_background_color !important;
        }

        .o_preview_name {
            color: $primary_text_color !important;
        }
    }
}

body.$mode_name {
    .o_mail_discuss {
        .o_mail_discuss_content {
            background-color: $dark_background_color !important;
        }
    }
}

body.$mode_name {
    .o_graph_controller {
        .o_graph_renderer {
            .o_graph_canvas_container {
                canvas {
                    background-color: $dark_background_color !important;
                }
            }
        }
    }
}

body.$mode_name {
    .o_control_panel {
        background: $light_dark_background_color !important;
        box-shadow: 0px 4px 16px $shadow_color !important;
        border-bottom: 1px solid $dark_border_color !important;
        z-index: 1;
        .o_panel {
            padding: 5px !important;
        }
    }
}

body.$mode_name {
    .list-group-item-action:hover, .list-group-item-action:focus {
        color: $link_hover_color;
        background-color: $light_background_color !important;
    }
}

body.$mode_name {
    .o_search_panel {

        background-color: $dark_background_color !important;
        color: $text_color !important;
        border-right: $dark_background_color !important;

        .list-group-item {
            background: 0 0 !important;
            background-color: $dark_background_color !important;
            .active {
                background-color: $light_background_color !important;
            }
        }
    }
}

body.$mode_name {
    .o_onboarding {
        border-bottom: none !important;
    }
}

body.$mode_name {
    .navigation {
        background-color: $dark_background_color !important;
    
        .navigation-menu-tab {
            background-color: $dark_background_color !important;
            border-right: 1px solid $dark_border_color !important;
            box-shadow: 0 -4px 25px 0 $shadow_color;
            header {
                background-color: $dark_background_color !important
            }
        }
    
        .navigation-menu-body {
            border-right: 1px solid $dark_border_color !important;
        }
    
        .navigation-menu-body {
            
            .navigation-section-name {
                border-bottom-color: $dark_border_color !important;
            }
    
            ul {
                li {
                    a {
                        color: $text_color !important;
    
                        &:focus,
                        &:hover {
                            background: 0 0 !important;
                            color: $link_hover_color !important;
                        }
    
                        &.active {
                            color: $link_text_hover_color! important;
                            background: $link_active_color !important;
                        }
                    }
    
                    a + ul li a.active {
                        color: $link_text_active_text_color!important;
                    }
    
                    &.open > a {
                        color: $primary_text_color !important;
                        background-color: $link_active_color !important
                    }
    
                    .dropdown-divider {
                        color: $light_border_color !important
                    }
                }
            }
        }
    
        .awesome-nav-footer {
            background: $dark_background_color !important;
            border-top-color: $dark_border_color !important;
            
            .awesome_footer .o_pager button {
                background-color: $secondary_color !important; 
            }
        }
        
        .board-pannel {
            .search_bar {
                .search_box {
                    background: $light_background_color !important;
                    .search_input {
                        background: $light_background_color !important;
                    }
                }
            }
        }
    }
}

body.$mode_name {
    .customizer {
        background: $dark_background_color !important;
        border-left-color: $dark_background_color !important;

        .top_title {
            border-bottom: 1px solid $dark_background_color !important;
            background: $dark_background_color !important;
            border-top: 1px solid $dark_background_color !important;
            background: $dark_background_color !important;
            box-shadow: 0 -4px 25px 0 $shadow_color !important;
        }
    
        .customizer-content {
            .style_item_container {
            
                .style_item_group {
                
                    .style_item_group_name {
                        border-top: 1px solid $light_background_color !important;
                        border-bottom: 1px solid $dark_border_color !important;
                        background-color: $light_background_color !important;
                    }
                    
                    .style_sub_group_name {
                        background: $light_background_color !important;
                        border-bottom: 1px solid $dark_border_color !important;
                        color: $text_color;
                    }
                }

                .add_new_group {
                    border-top: 1px solid $light_border_color !important;
                    border-bottom: 1px solid $dark_border_color !important;
                    background-color: $light_background_color !important;
                }
            }

            .settings {
                .tab-content {
                    .tab-pane {
                        background: $dark_background_color !important;
                        border-color: $dark_background_color !important;
                    }
                }
            }

            .style-preview-box {
                box-shadow: 0 2px 10px $shadow_color !important;
            }
            
            .theme_mode_tool_bar {
                border-top: 1px solid $dark_border_color;
                border-bottom: 1px solid $dark_border_color;
                background-color: $light_background_color;
            }
        }

        .theme_styles {
            .style_item_container {
                .theme-style-nav-item {
                    background: transparent !important;
                }

                .style_items {
                    padding: 0px !important;
                }
            }
        }

        .style-preview-box {
            border-color: $primary_border_color !important;
            .sidebar-box {
                border-right-color: $primary_border_color !important;
            }
        }

        .theme-mode-container {
            .theme_style_tab{
                &.active {
                    background: transparent !important;
                }
            }
        }

        .customizer-footer {
            border-top: 1px solid $dark_background_color !important;
            background: $dark_background_color !important;
            box-shadow: 0 -4px 25px 0 $shadow_color !important;
        }
    }
}

body.$mode_name {
    .o_form_view {
        .o_form_statusbar {

            background-color: $dark_background_color !important;
            border: 1px solid $dark_background_color !important;
            padding-left: 25px !important;
            
            & > .o_statusbar_status {
                & > .o_arrow_button:not(:first-child) {
                    &:after {
                        border-left: 11px solid $dark_background_color !important;
                    }

                    &:before {
                        border-left-color: $dark_background_color !important;
                    }
                }

                .o_arrow_button.btn-primary.disabled {
                    background-color: $dark_background_color !important;
                    &:after {
                        border-left-color: $dark_background_color !important;
                    }
                }

                .o_arrow_button.disabled {
                    border-left: 1px solid #585f79 !important;
                }
            }
        }

        .o_required_modifier{
            &.o_input, .o_input {
                background-color: $dark_background_color !important;
            }
        }
    }
}

body.$mode_name {
    .note-editor {
        border: 1px solid $dark_background_color !important;
        .note-editing-area {
            .note-editable {
                background-color: $dark_background_color !important;
                color: #c7c7c7 !important;
            }
        }

        .note-statusbar {
            background-color: $primary_border_color !important;
        }

        .panel-heading.note-toolbar {
            border-bottom: 1px solid $dark_background_color !important;
            background-color: $dark_background_color !important;
    
            .btn {
                border-left: none !important;
                border-right: none !important;
                background: transparent !important
            }
        }
    }
}

body.$mode_name {
    .alert-info {
        border-color: $dark_background_color !important;
    }
}

body.$mode_name {
    .o_widget_Discuss {
        .o_Discuss_content {
            border-top: none !important;
        }

        .o_MessageList {
            background-color: $dark_background_color !important;
        }
    
        .o_DiscussSidebar {
            background-color: $dark_background_color !important;
        }
    }

    .o_MessagingMenu {
        .o_MessagingMenu_notificationList {
            background-color: $dark_background_color !important;
    
            .o_NotificationList_notificationRequest, .o_NotificationGroup, .o_ThreadPreview {
                background-color: $dark_background_color !important;
                &:hover {
                    background-color: $dark_background_color !important;
                }
            }
    
            .o_NotificationList_separator {
                border-bottom: 1px solid $dark_background_color !important;
            }
        }

        .o_MessagingMenu_dropdownMenuHeader {
            border-bottom: 1px solid $dark_background_color !important;
        }
    }
}

body.$mode_name { 
    .o_field_widget{
        &.o_field_many2manytags {
            .o_tag_color_0 {
                background-color: $dark_background_color !important;
                color: $primary_text_color !important;
                box-shadow: inset 0 0 0 2px $dark_background_color !important;
            }
        }
    }
}

body.$mode_name {
    .o_setting_search {
        background: $dark_background_color !important;
        border: 1px solid $dark_background_color !important;

        input {
            border-bottom: none !important;
            background: $dark_background_color !important;
            color: $primary_text_color !important;
        }

        .searchIcon {
            right: 10px !important;
        }
    }

    .o_base_settings {
        .o_setting_container{
            .settings {
                background-color: $dark_background_color !important;
                & > .app_settings_block h2 {
                    padding: 0.75rem 16px !important;
                    background-color: $dark_background_color !important;
                }
            }

             .settings_tab {
                background: $dark_background_color !important;
                .selected {
                    background-color: $dark_background_color !important;
                    box-shadow: inset 3px 0 0 $shadow_color !important;
                }
            }
        }
    }
}

body.$mode_name {
    .navigation-menu-tab-header{

        .user_profile_header_image {
            background: $dark_background_color !important;
        }
    
        .dropdown-menu {
            background: $dark_background_color !important;

            .dropdown-menu-body {
                background: $dark_background_color !important;
            }
    
            .user_profile_footer {
                background: $dark_background_color !important;
            }
        }
    }
}


body.$mode_name {
    .o_calendar_view {
        background-color: $dark_background_color !important;
        background: linear-gradient(-45deg, $dark_background_color, $dark_background_color) !important;

        .o_calendar_widget {

            color: $primary_text_color !important;

            td {
                border-color: $primary_border_color !important;
            }

            .fc-widget-header {
                border-bottom-color: $primary_border_color !important;
            }

            .fc-timeGridDay-view, .fc-timeGridWeek-view {
                tbody {
                    td {
                        border-top-color: $primary_border_color !important;
                    }
                }
            }
            
            .fc-body {
                > tr {
                    > td {
                        border-color: $primary_border_color !important;
                    }
                }
            }

            .fc-day-grid {
                background-color: $dark_background_color !important;
                .fc-row {
                    border-bottom: none !important;
                }
            }

            .fc-widget-content {
                background-color: $dark_background_color !important;
            }

            hr.fc-widget-header {
                background: $primary_border_color !important;
            }

           .fc-slats tr:first-child td.fc-widget-content:last-child {
                box-shadow: inset 0 1px 0 $dark_background_color !important;
            }

            .fc-dayGridMonth-view {
                .fc-bg {
                    .fc-today {
                        background: $dark_background_color !important;
                        border-color: $primary_border_color !important;
                    }
                }
            }

            .fc-dayGridMonth-view .fc-day-number {
                color: $primary_text_color !important;
            }
        }
    }

    .o_calendar_sidebar_container {
        background-color: $dark_background_color !important;
        border-left: 1px solid $primary_border_color !important;

        .o_calendar_mini  {
            .ui-widget-content {
                border: 1px solid $primary_border_color !important;
                background: $dark_background_color !important;
                color: $primary_text_color !important;
            }
        }
    }
}


body.$mode_name {

    ::-webkit-scrollbar-track {
        background: $dark_background_color !important;
    }

    ::-webkit-scrollbar-thumb {
        background: $light_background_color !important;
    }

    ::-webkit-scrollbar-thumb:increment,
    ::-webkit-scrollbar-thumb:decrement {
        background: $light_background_color !important;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: $light_background_color !important;
    }
}
"""