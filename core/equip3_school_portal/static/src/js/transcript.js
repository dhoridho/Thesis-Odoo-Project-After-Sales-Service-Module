$(document).ready(function(){
    $("#transcript-modal").modal("show");
    $("#input-student-id").select2({
        placeholder: "Choose Student",
    });
    $("#input-program-id").select2({
        placeholder: "Choose Program",
    });
    $("#input-intake-id").select2({
        placeholder: "Choose Intake",
    });
});