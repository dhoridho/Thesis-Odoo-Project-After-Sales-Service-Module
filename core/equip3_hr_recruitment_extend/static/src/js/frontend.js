$(document).ready(function () { 

  var pathname = window.location.pathname
  if(pathname.includes("/interview/invite/schedule")){
   let searchParams = new URLSearchParams(window.location.search); 
   var nameapplicant = searchParams.get('name');
   var emailapplicant = searchParams.get('email');
   var phoneapplicant = searchParams.get('phone');
   var idapplicant = searchParams.get('applicant_id');
   if(nameapplicant) {
      $('.detail_name_invite input[name="name"]').val(nameapplicant)
   }
   if(emailapplicant) {
      $('.detail_name_invite input[name="email"]').val(emailapplicant)
   }
   if(phoneapplicant) {
      $('.detail_name_invite input[name="phone"]').val(phoneapplicant)
   }
   if(idapplicant) {
      $('.detail_name_invite input[name="applicant_id"]').val(idapplicant)
   }

   $('#submit_schedule_meeting').click(function(){
      var check = $('.calendar-invite-timeslot.active').length
      if (check<=0){
         $('#modal_notif').modal()
      }
      else{
        $('.click_button').click()
      }
    })

   $('#reason_cancel_interview').click(function(){
      $('#modal_reason_cancel_interview').modal()
    })

var calMonthName = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec"
      ]
if ($('.calendareventlist').length > 0) {
  function CalendarControl() {
  
    const calendar = new Date();
    const calendarControl = {
      localDate: new Date(),
      prevMonthLastDate: null,
      calWeekDays: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
      calMonthName: calMonthName,
      daysInMonth: function (month, year) {
        return new Date(year, month, 0).getDate();
      },
      firstDay: function () {
        return new Date(calendar.getFullYear(), calendar.getMonth(), 1);
      },
      lastDay: function () {
        return new Date(calendar.getFullYear(), calendar.getMonth() + 1, 0);
      },
      firstDayNumber: function () {
        return calendarControl.firstDay().getDay() + 1;
      },
      lastDayNumber: function () {
        return calendarControl.lastDay().getDay() + 1;
      },
      getPreviousMonthLastDate: function () {
        let lastDate = new Date(
          calendar.getFullYear(),
          calendar.getMonth(),
          0
        ).getDate();
        return lastDate;
      },
      navigateToPreviousMonth: function () {
        calendar.setMonth(calendar.getMonth() - 1);
        calendarControl.attachEventsOnNextPrev();
      },
      navigateToNextMonth: function () {
        calendar.setMonth(calendar.getMonth() + 1);
        calendarControl.attachEventsOnNextPrev();
      },
      navigateToCurrentMonth: function () {
        let currentMonth = calendarControl.localDate.getMonth();
        let currentYear = calendarControl.localDate.getFullYear();
        calendar.setMonth(currentMonth);
        calendar.setYear(currentYear);
        calendarControl.attachEventsOnNextPrev();
      },
      displayYear: function () {
        let yearLabel = document.querySelector(".calendar-meeting-invite .calendar-year-label");
        yearLabel.innerHTML = calendar.getFullYear();
      },
      displayMonth: function () {
        let monthLabel = document.querySelector(
          ".calendar-meeting-invite .calendar-month-label"
        );
        monthLabel.innerHTML = calendarControl.calMonthName[calendar.getMonth()];
      },
      selectDate: function (e) {
        console.log(
          `${e.target.textContent} ${
            calendarControl.calMonthName[calendar.getMonth()]
          } ${calendar.getFullYear()}`
        );
      },
      plotSelectors: function () {
        document.querySelector(
          ".calendar-meeting-invite"
        ).innerHTML += `<div class="calendar-inner"><div class="calendar-controls">
          <div class="calendar-prev" style="visibility: hidden;"><a href="#"><svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128"><path fill="#666" d="M88.2 3.8L35.8 56.23 28 64l7.8 7.78 52.4 52.4 9.78-7.76L45.58 64l52.4-52.4z"/></svg></a></div>
          <div class="calendar-year-month">
          <div class="calendar-month-label"></div>
          <div>-</div>
          <div class="calendar-year-label"></div>
          </div>
          <div class="calendar-next"><a href="#"><svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128"><path fill="#666" d="M38.8 124.2l52.4-52.42L99 64l-7.77-7.78-52.4-52.4-9.8 7.77L81.44 64 29 116.42z"/></svg></a></div>
          </div>
          <div class="calendar-today-date">Today: 
            ${calendarControl.calWeekDays[calendarControl.localDate.getDay()]}, 
            ${calendarControl.localDate.getDate()}, 
            ${calendarControl.calMonthName[calendarControl.localDate.getMonth()]} 
            ${calendarControl.localDate.getFullYear()}
          </div>
          <div class="calendar-body"></div></div>`;
      },
      plotDayNames: function () {
        for (let i = 0; i < calendarControl.calWeekDays.length; i++) {
          document.querySelector(
            ".calendar-meeting-invite .calendar-body"
          ).innerHTML += `<div>${calendarControl.calWeekDays[i]}</div>`;
        }
      },
      plotDates: function () {
        document.querySelector(".calendar-meeting-invite .calendar-body").innerHTML = "";
        calendarControl.plotDayNames();
        calendarControl.displayMonth();
        calendarControl.displayYear();
        let count = 1;
        let prevDateCount = 0;
  
        calendarControl.prevMonthLastDate = calendarControl.getPreviousMonthLastDate();
        let prevMonthDatesArray = [];
        let calendarDays = calendarControl.daysInMonth(
          calendar.getMonth() + 1,
          calendar.getFullYear()
        );
        // dates of current month
        for (let i = 1; i < calendarDays; i++) {
          if (i < calendarControl.firstDayNumber()) {
            prevDateCount += 1;
            document.querySelector(
              ".calendar-meeting-invite .calendar-body"
            ).innerHTML += `<div class="prev-dates"></div>`;
            prevMonthDatesArray.push(calendarControl.prevMonthLastDate--);
          } else {
            document.querySelector(
              ".calendar-meeting-invite .calendar-body"
            ).innerHTML += `<div class="number-item" data-num=${count}><a class="dateNumber" href="#">${count++}</a></div>`;
          }
        }
        //remaining dates after month dates
        for (let j = 0; j < prevDateCount + 1; j++) {
          document.querySelector(
            ".calendar-meeting-invite .calendar-body"
          ).innerHTML += `<div class="number-item" data-num=${count}><a class="dateNumber" href="#">${count++}</a></div>`;
        }
        calendarControl.highlightToday();
        calendarControl.plotPrevMonthDates(prevMonthDatesArray);
        calendarControl.plotNextMonthDates();
      },
      attachEvents: function () {
        let prevBtn = document.querySelector(".calendar-meeting-invite .calendar-prev a");
        let nextBtn = document.querySelector(".calendar-meeting-invite .calendar-next a");
        let todayDate = document.querySelector(".calendar-meeting-invite .calendar-today-date");
        let dateNumber = document.querySelectorAll(".calendar-meeting-invite .dateNumber");
        prevBtn.addEventListener(
          "click",
          calendarControl.navigateToPreviousMonth
        );
        nextBtn.addEventListener("click", calendarControl.navigateToNextMonth);
        todayDate.addEventListener(
          "click",
          calendarControl.navigateToCurrentMonth
        );
        for (var i = 0; i < dateNumber.length; i++) {
            dateNumber[i].addEventListener(
              "click",
              calendarControl.selectDate,
              false
            );
        }
      },
      highlightToday: function () {
        let currentMonth = calendarControl.localDate.getMonth() + 1;
        let changedMonth = calendar.getMonth() + 1;
        let currentYear = calendarControl.localDate.getFullYear();
        let changedYear = calendar.getFullYear();
        if (
          currentYear === changedYear &&
          currentMonth === changedMonth &&
          document.querySelectorAll(".number-item")
        ) {
          document
            .querySelectorAll(".number-item")
            [calendar.getDate() - 1].classList.add("calendar-today");
        }
      },
      plotPrevMonthDates: function(dates){
        dates.reverse();
        for(let i=0;i<dates.length;i++) {
            if(document.querySelectorAll(".prev-dates")) {
                document.querySelectorAll(".prev-dates")[i].textContent = dates[i];
            }
        }
      },
      plotNextMonthDates: function(){
       let childElemCount = document.querySelector('.calendar-body').childElementCount;
       //7 lines
       if(childElemCount > 42 ) {
           let diff = 49 - childElemCount;
           calendarControl.loopThroughNextDays(diff);
       }

       //6 lines
       if(childElemCount > 35 && childElemCount <= 42 ) {
        let diff = 42 - childElemCount;
        calendarControl.loopThroughNextDays(42 - childElemCount);
       }

      },
      loopThroughNextDays: function(count) {
        if(count > 0) {
            for(let i=1;i<=count;i++) {
                document.querySelector('.calendar-body').innerHTML += `<div class="next-dates">${i}</div>`;
            }
        }
      },
      attachEventsOnNextPrev: function () {
        calendarControl.plotDates();
        calendarControl.attachEvents();
        calendarControl.setToSchedule();
        calendarControl.actToSchedule();
        calendarControl.dontBackprvmontnow();
      },
      dontBackprvmontnow: function () {
        var date_month =  $('.calendar-month-label').text() 
     var date_month = (parseInt(calMonthName.indexOf( date_month )) + 1).toString();
     var d = new Date()
      var n = d.getMonth()
      if(date_month==n+1){
        $('.calendar-prev').css("visibility", "hidden");
      }
      else{
        $('.calendar-prev').css("visibility", "inherit");
      }
      },
      setToSchedule: function () {
        $('.calendar-meeting-invite .number-item').each(function( i ) {
        var date_month =  $('.calendar-month-label').text() 
        var date_month = (parseInt(calMonthName.indexOf( date_month )) + 1).toString();
        if (date_month.length == 1){
          date_month = '0'+date_month
        }
        var date_check = $(this).data('num').toString()
        if (date_check.length == 1){
          date_check = '0'+date_check
        }
        var only_date = date_check
        var date_check =  $('.calendar-year-label').text() +'-'+date_month+'-'+date_check
        var check_list = $('.calendareventlist p:contains('+date_check+')')

        if(check_list.length<=0) {

          $(this).replaceWith( "<div class='prev-dates'>"+only_date+"</div>" );
        }

    })
      },
      actToSchedule: function () {
        $('.calendar-meeting-invite .number-item').click(function(){
        $('.calendar-meeting-invite .number-item').removeClass('active')
        $(this).addClass('active')
        $('.list_calendar-invite-timeslot .calendar-invite-timeslot').remove()
        var date_click = $(this).data('num').toString()
        if (date_click.length == 1){
          date_click = '0'+date_click
        }
        var date_month =  $('.calendar-month-label').text() 
        var date_month = (parseInt(calMonthName.indexOf( date_month )) + 1).toString();
        if (date_month.length == 1){
          date_month = '0'+date_month
        }
        var date_click =  $('.calendar-year-label').text() +'-'+date_month+'-'+date_click
        var check_list = $('.calendareventlist p:contains('+date_click+')')
        var calendar_invite_timeslot = ''
        var check_double = []
        check_list.each(function( i ) {
          var schedule = $(this).data('schedule')
          schedule = schedule.replace(/'/g, '"');
          schedule = (JSON.parse(schedule)).sort();
          var timeslot = $(this).data('timeslot')
          var interviewer = $(this).data('interviewer')
          var resultid = $(this).data('id')
          for (let i = 0; i < schedule.length; ++i) {

            $('.list_calendar-invite-timeslot').append( '<div data-date_click="'+date_click+'" data-id="'+resultid+'" data-interviewer="'+interviewer+'" data-timeslot='+timeslot+' class="calendar-invite-timeslot" style="margin-bottom: 14px;"><div><span>'+schedule[i]+'</span></div></div>');
          }
            
            $('.calendar-invite-timeslot').click(function(){
              $('.calendar-invite-timeslot').removeClass('active')
              $(this).addClass('active')
              var interviewer1 = $(this).data('interviewer')
              var calendar_id = $(this).data('id')
              // var date_calendar = $(this).data('date_click')
              var time_calendar = $(this).text()
              $('input[name="calendar_id"]').val(calendar_id)
              // $('input[name="date"]').val(date_calendar)
              $('input[name="time"]').val(time_calendar)
              $('.interviewer_p').remove()
              $('<p class="interviewer_p" style="margin-top: 30px;margin-bottom: 30px;"><b>Interviewer</b> : '+interviewer1+'</p>').insertBefore('.detail_name_invite button')
            })
            
        })
          

        

      })
      },
      init: function () {
        calendarControl.plotSelectors();
        calendarControl.plotDates();
        calendarControl.attachEvents();
        calendarControl.setToSchedule();
        calendarControl.actToSchedule();
      }
    };
    calendarControl.init();
  }
  
  const calendarControl = new CalendarControl(); 

  }
}


  if ($('.job_header_flex_to_top').length > 0){
    $(".job_header_flex_to_top").appendTo(".header1jobs");
  }
  $('.table_past_experience_table_add_line').click(function(){
    var line = '<tr class="input_data">'
                +'<td style="padding: unset;"><input name="start_date_pe" readonly="1" class="form-control usedatepicker" type="text" style="padding: unset;padding-left: 5px;font-size: 14px;"></td>'
                +'<td style="padding: unset;"><input name="end_date_pe" readonly="1" class="form-control usedatepicker" type="text" style="padding: unset;padding-left: 5px;font-size: 14px;"></td>'
                +'<td style="padding: unset;" class="text-center"><input name="is_currently_work_here_pe" readonly="1"  type="checkbox" style="padding: unset;margin-top: 10px;font-size: 14px;"></td>'
                +'<td style="padding: unset;"><input name="company_name_pe" class="form-control" type="text" style="font-size: 14px;"></td>'
                +'<td style="padding: unset;"><input name="position_pe" class="form-control" type="text" style="font-size: 14px;"></td>'
                +'<td style="padding: unset;"><input name="job_descriptions_pe" class="form-control" type="text" style="font-size: 14px;"></td>'
                +'<td style="padding: unset;"><input name="reason_pe" class="form-control" type="text" style="font-size: 14px;"></td>'
                +'<td style="padding: unset;"><input name="salary_pe" class="form-control" type="number" style="font-size: 14px;"></td>'
                +'<td style="padding: unset;"><input name="company_phone_pe" class="form-control" type="text" style="font-size: 14px;"></td>'
                +'<td style="padding: unset;" class="text-center"><i class="fa fa-trash" style="cursor:pointer;"></i></td>'
            +'</tr>';

        $(line).insertBefore( '.table_past_experience_table_add_line');
        $('input[name="is_currently_work_here_pe"]').click(function(){
      if($(this).is(":checked")){
        $($($(this).parents()[1]).find('input[name="end_date_pe"]')).val('')
        $($($(this).parents()[1]).find('input[name="end_date_pe"]')).datepicker("destroy");
        $($($(this).parents()[1]).find('input[name="end_date_pe"]')).removeClass('usedatepicker')
      }
      else{
        $($($(this).parents()[1]).find('input[name="end_date_pe"]')).datepicker({ 
                dateFormat:'dd/mm/yy',changeMonth: true,changeYear: true,
                 allowInputToggle: true 
            }); 
      }
    });
        $('.usedatepicker').datepicker({ 
            dateFormat:'dd/mm/yy',changeMonth: true,changeYear: true,
             allowInputToggle: true 
        }); 
        $('#table_past_experience_table .fa-trash').click(function(){
          $($(this).parents()[1]).remove()
        });

  });

  


  setTimeout(function(){ 
             

  $('input[name="have_exp"]').click(function(){
    if($('input[name="have_exp"]').is(":checked")){
      $('.table_exp_question').hide()
    }
    else{
      $('.table_exp_question').show()
    }
  });
}, 2000);



  var pathname = window.location.pathname
  if($('.o_website_hr_recruitment_jobs_list').length>0){
    if(!pathname.includes("/jobs")){
      window.location.href = '/jobs'
    }
  }
  if(pathname.includes("/jobs")||pathname.includes("/job-thank-you")){
    if($('#gotojoinposition').length > 0){
      $('header nav').css("position", "absolute");
      $('header nav').css("width", "100%");
    }
    // $('#top_menu_container img').css("filter", "brightness(0) invert(1)");
    $('header nav').css("background-color", "white");
    $('header nav').css("padding", "20px 0");
    
    $('header').css("background", "transparent");
    $('ul#top_menu li').remove();
    $('#oe_structure_header_default_1').remove();
    $('#top_menu_container a').attr('href','/jobs')
    // $('#top_menu_container img').attr('src','/equip3_hr_recruitment_extend/static/src/img/logowhite.png')
  }
  if ($(".slick_testimoni_jobs").hasClass('slick-initialized slick-slider slick-dotted o_colored_level')){
     var box_testimoni_jobs = []
     var many_data_lick = $('ul.slick-dots li').length
     var count_lick = 0
     $( ".box_testimoni_jobs" ).each(function( index ) {
        count_lick+=1
        if(count_lick<=many_data_lick){
          box_testimoni_jobs.push({
            'title':$.trim($(this).find('.box_testimoni_jobs_title').text()),
            'content':$.trim($($($(this).find('p'))[1]).text()),
            'name_testimoni_job':$.trim($($($(this).find('p'))[2]).text()),
            'position_testimoni_job':$.trim($($($(this).find('p'))[3]).text()),
            'image':$.trim($($($(this).find('img'))).attr('src')),
          })
        }
          
      });

    $(".slick_testimoni_jobs").replaceWith(' \
        <section class="slick_testimoni_jobs">\
        </section>\
      '
      )
    for (index = 0; index < box_testimoni_jobs.length; ++index) {

      $(".slick_testimoni_jobs").append('\
          <div>\
            <div style="background:white;" class="box_testimoni_jobs">\
              <p class="text-center box_testimoni_jobs_title"><b>'+box_testimoni_jobs[index]['title']+'</b></p>\
              <p class="text-left">'+box_testimoni_jobs[index]['content']+'</p>\
              <br/>\
              <div style="display:-webkit-box;">\
                  <img src="'+box_testimoni_jobs[index]['image']+'" class="img-responsive" style="width:70px;"/>\
                  <div style="left: 12px;top: 12px;position: relative;text-align: left;">\
                      <p style="margin:unset;" class="name_testimoni_job"><b>'+box_testimoni_jobs[index]['name_testimoni_job']+'</b></p>\
                      <p>'+box_testimoni_jobs[index]['position_testimoni_job']+'</p>\
                  </div>\
              </div>\
            </div>\
          </div>\
        ');
    };



  }
    if ($( window ).width() > 865){
      $(".slick_testimoni_jobs").slick({
            dots: true,
            infinite: true,
            centerMode: true,
            slidesToShow: 1,
            centerPadding:'200px',
            slidesToScroll: 3
          });
    }
    else if ($( window ).width() > 460){
      $(".slick_testimoni_jobs").slick({
            dots: true,
            infinite: true,
            centerMode: true,
            slidesToShow: 1,
            centerPadding:'40px',
            slidesToScroll: 3
          });
    }
    else{
      $(".slick_testimoni_jobs").slick({
            dots: true,
            infinite: true,
            centerMode: true,
            slidesToShow: 1,
            centerPadding:'30px',
            slidesToScroll: 3
          });
    }

    $('.job_header_flex select').select2({
    });


    $('#job_view_all_role').click(function(event) {
      window.location.href= '/jobs?all=1'+'#gotojoinposition'
    })    

    if(window.location.href.includes("/jobs?all=1#gotojoinposition")) {
          setTimeout(function(){ 
              $('.bottom_job_see_more').click()
           }, 3000);
    }

    $('.bottom_job_see_more').click(function(event) {
      $('.col-box-job-recruit').removeClass('d-none');
      $($('.bottom_job_see_more').parent()).hide();
    })  

    $('.header1jobs .job_header1_flex_button').click(function(event) {
      var urllink = '/jobs'
      var location_id = $('.header1jobs .div_job_select_location select').val()
      var job_name = $('.header1jobs .div_job_select_role input').val()

      if (location_id!='0') {
        urllink+='/office/'+location_id
      }
      if (job_name!='') {
        urllink+='?jobname='+job_name
      }
      window.location.href= urllink+'#gotojoinposition'
    });
    $('.header3jobs .job_header1_flex_button').click(function(event) {
      var urllink = '/jobs'
      var location_id = $('.header3jobs .div_job_select_location select').val()
      var job_name = $('.header3jobs .div_job_select_role input').val()
      var departement_id = $('.header3jobs .div_job_select_departement select').val()
      if (departement_id!='0') {
        urllink+='/department/'+departement_id
      }

      if (location_id!='0') {
        urllink+='/office/'+location_id
      }
      if (job_name!='') {
        urllink+='?jobname='+job_name
      }
      window.location.href= urllink+'#gotojoinposition'

    });
  



  odoo.define('mccoy_website.website_json', function(require) {
      "use strict";
      var ajax = require('web.ajax');

      $('.table_emp_skill_table_add_line').click(function(){
        var $table = $(this)
      var selectskilltype = '<select name="skill_type_id_pe" class="selectskilltype form-control"><option value="0"></option>'
      ajax.jsonRpc("/get-skill-type", 'call', {

      }).then(function(result) {
        for (var i = 0; i < result.length; i++) {
                        selectskilltype +='<option value='+result[i]['id']+'>'+result[i]['name']+'</option>';
                    }
                selectskilltype+='</select>'
                var line = '<tr class="input_data">'
                    +'<td  style="padding: unset;">'+selectskilltype+'</td>'
                    +'<td id="selectskillonly" style="padding: unset;"></td>'
                    +'<td id="selectskilllevel" style="padding: unset;"></td>'
                    +'<td style="padding: unset;" class="text-center"><i class="fa fa-trash" style="cursor:pointer;"></i></td>'
                +'</tr>';

            $(line).insertBefore( '.table_emp_skill_table_add_line');
            $( "select.selectskilltype" ).each(function( i ) {
              if($(this).css('display')!='none'){
                $(this).select2();
              }
                
         });
            $('#table_emp_skill_table .fa-trash').click(function(){
              $($(this).parents()[1]).remove()
            });

            $( "select.selectskilltype" ).change(function(){
              var $this = $(this)
              var idskilltype= $(this).val()
              if(idskilltype && idskilltype!='0' && idskilltype!=0){
                var selectskill = '<select name="skill_id_pe" class="selectskillonly form-control"><option value="0"></option>'
                var selectlevel = '<select name="skill_level_id_pe" class="selectskilllevel form-control"><option value="0"></option>'
            ajax.jsonRpc("/get-skill-other-list", 'call', {
              'skill_type_id':parseInt(idskilltype),
            }).then(function(result) {
              for (var i = 0; i < result['skill'].length; i++) {
                            selectskill +='<option value='+result['skill'][i]['id']+'>'+result['skill'][i]['name']+'</option>';
                        }
                        for (var i = 0; i < result['level'].length; i++) {
                            selectlevel +='<option value='+result['level'][i]['id']+'>'+result['level'][i]['name']+'</option>';
                        }
                        selectskill+='</select>'
                        selectlevel+='</select>'
                        var $tr = $($this.parents()[1])
                        var checkfield = $tr.find('#selectskillonly')
                        var checkfield1 = $tr.find('#selectskilllevel')
                        if (checkfield.length>0){
                          $(checkfield).empty()
                        }
                        if (checkfield1.length>0){
                          $(checkfield1).empty()
                        }

                        $(checkfield).append(selectskill);
                        $(checkfield1).append(selectlevel);
                        $( "select.selectskillonly" ).each(function( i ) {
                    if($(this).css('display')!='none'){
                      $(this).select2();
                    }
                      
               });
                        $( "select.selectskilllevel" ).each(function( i ) {
                    if($(this).css('display')!='none'){
                      $(this).select2();
                    }
                      
               });
            });
              }
            });

      });

    });

      



  });
})